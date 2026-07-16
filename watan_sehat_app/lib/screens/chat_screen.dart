import 'dart:async';
import 'dart:math' as math;
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/chat_provider.dart';
import '../services/api_service.dart';
import 'settings_screen.dart';

enum VoiceState { idle, listening, processing, speaking }

class ChatScreen extends StatefulWidget {
  @override
  _ChatScreenState createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ApiService _apiService = ApiService();
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioPlayer _tonePlayer = AudioPlayer();
  final AudioRecorder _audioRecorder = AudioRecorder();
  StreamSubscription? _amplitudeSub;

  bool _isVoiceMode = false;
  bool _speechEnabled = false;

  // ── Voice state ──────────────────────────────────────────────────
  VoiceState _voiceState = VoiceState.idle;
  String _recognizedWords = '';      // partial STT words live
  String _aiResponseText = '';       // streams in token by token

  // ── P2: Real waveform via scrolling sound-level buffer ───────────
  final List<double> _waveformBuffer = List<double>.filled(35, 0.0);
  int _waveformWriteIdx = 0;
  double _soundLevel = 0.0;

  // ── P5: VAD — auto-send after 1.2 s silence post-speech ─────────
  bool _speechDetectedInSession = false;
  DateTime? _silenceStart;

  // ── P1: Sentence queue for chunked TTS ──────────────────────────
  final List<String> _pendingSentences = [];
  bool _ttsActive = false;
  String _sentenceAccumulator = '';
  static final _sentenceSplitter = RegExp(r'(?<=[.!?؟۔])\s+');

  // ── Fallback animation for processing / speaking states ─────────
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2500),
    )..repeat();
    _initSpeech();
  }

  void _initSpeech() async {
    _speechEnabled = await _audioRecorder.hasPermission();
    setState(() {});
  }

  // ── P5: VAD ─────────────────────────────────────────────────────
  void _onSoundLevel(double level) {
    setState(() {
      _soundLevel = level;
      _waveformBuffer[_waveformWriteIdx % 35] = level;
      _waveformWriteIdx++;
    });

    if (_voiceState != VoiceState.listening) return;

    if (level > 1.5) {
      _speechDetectedInSession = true;
      _silenceStart = null;
    } else if (_speechDetectedInSession) {
      _silenceStart ??= DateTime.now();
      if (DateTime.now().difference(_silenceStart!) >
          const Duration(milliseconds: 1200)) {
        _sendVoiceQuery();
        _speechDetectedInSession = false;
        _silenceStart = null;
      }
    }
  }

  void _startListening() async {
    await _audioPlayer.stop();
    await _amplitudeSub?.cancel();
    _amplitudeSub = null;
    _speechDetectedInSession = false;
    _silenceStart = null;
    setState(() {
      _voiceState = VoiceState.listening;
      _recognizedWords = '';
      _aiResponseText = '';
      _sentenceAccumulator = '';
      _pendingSentences.clear();
    });

    await _playUiTone(start: true);

    if (await _audioRecorder.hasPermission()) {
      final Directory tempDir = await getTemporaryDirectory();
      final String path = '${tempDir.path}/stt_audio.wav';

      await _audioRecorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        ),
        path: path,
      );

      _amplitudeSub = _audioRecorder.onAmplitudeChanged(const Duration(milliseconds: 100)).listen((event) {
        if (_voiceState != VoiceState.listening) return;
        double level = math.max(0.0, (event.current + 40) / 4);
        _onSoundLevel(level);
      });
    }
  }

  // Generates and plays a short UI tone (ascending = start listening, descending = done)
  Future<void> _playUiTone({required bool start}) async {
    const sampleRate = 44100;
    const durationMs = 180;
    final samples = (sampleRate * durationMs / 1000).round();
    final f1 = start ? 660.0 : 880.0;
    final f2 = start ? 880.0 : 550.0;

    final wav = ByteData(44 + samples * 2);
    // RIFF header
    wav.setUint32(0, 0x52494646, Endian.big);
    wav.setUint32(4, 36 + samples * 2, Endian.little);
    wav.setUint32(8, 0x57415645, Endian.big);
    wav.setUint32(12, 0x666d7420, Endian.big);
    wav.setUint32(16, 16, Endian.little);
    wav.setUint16(20, 1, Endian.little);
    wav.setUint16(22, 1, Endian.little);
    wav.setUint32(24, sampleRate, Endian.little);
    wav.setUint32(28, sampleRate * 2, Endian.little);
    wav.setUint16(32, 2, Endian.little);
    wav.setUint16(34, 16, Endian.little);
    wav.setUint32(36, 0x64617461, Endian.big);
    wav.setUint32(40, samples * 2, Endian.little);
    for (int i = 0; i < samples; i++) {
      final t = i / sampleRate;
      final freq = f1 + (f2 - f1) * i / samples;
      final fadeIn = math.min(1.0, i / (sampleRate * 0.015));
      final fadeOut = math.min(1.0, (samples - i) / (sampleRate * 0.03));
      final sample = (math.sin(2 * math.pi * freq * t) * fadeIn * fadeOut * 0.35 * 32767).round().clamp(-32768, 32767);
      wav.setInt16(44 + i * 2, sample, Endian.little);
    }
    try {
      await _tonePlayer.play(BytesSource(wav.buffer.asUint8List()));
      await _tonePlayer.onPlayerComplete.first.timeout(const Duration(milliseconds: 500));
    } catch (_) {}
  }

  void _sendVoiceQuery() async {
    if (_voiceState == VoiceState.listening) {
      final path = await _audioRecorder.stop();
      _audioPlayer.stop();
      if (path != null) {
        setState(() {
          _voiceState = VoiceState.processing;
          _recognizedWords = 'Transcribing...';
        });
        final transcript = await _apiService.transcribeVoice(path);
        if (transcript != null && transcript.isNotEmpty) {
          _recognizedWords = transcript;
          _processVoiceQueryStreaming();
        } else {
          setState(() {
            _voiceState = VoiceState.idle;
            _recognizedWords = '';
          });
        }
      }
    }
  }

  // ── P1 + P4: Streaming voice processing ─────────────────────────
  Future<void> _processVoiceQueryStreaming() async {
    final query = _recognizedWords;
    setState(() {
      _voiceState = VoiceState.processing;
      _aiResponseText = '';
      _sentenceAccumulator = '';
      _pendingSentences.clear();
      _ttsActive = false;
    });

    final chatProvider = Provider.of<ChatProvider>(context, listen: false);
    chatProvider.addMessage(query, true);
    final history = chatProvider.getChatHistory();

    final prefs = await SharedPreferences.getInstance();
    final useOnlineGemini = prefs.getBool('use_online_gemini') ?? false;
    final geminiApiKey = prefs.getString('active_gemini_api_key') ?? '';

    final onToken = (String token) {
      if (!mounted || !_isVoiceMode) return;
      setState(() {
        _aiResponseText += token;
        _sentenceAccumulator += token;
      });

      // Extract complete sentences and queue for TTS
      final parts = _sentenceAccumulator.split(_sentenceSplitter);
      if (parts.length > 1) {
        for (int i = 0; i < parts.length - 1; i++) {
          final sentence = parts[i].trim();
          if (sentence.isNotEmpty) _enqueueSentence(sentence);
        }
        _sentenceAccumulator = parts.last;
      }
    };

    final onDone = () {
      if (!mounted) return;
      // Flush any remaining text
      if (_sentenceAccumulator.trim().isNotEmpty) {
        _enqueueSentence(_sentenceAccumulator.trim());
        _sentenceAccumulator = '';
      }
      chatProvider.addMessage(_aiResponseText, false);
      if (!_ttsActive) {
        // Nothing queued (rule was very short or TTS already done)
        Future.delayed(const Duration(milliseconds: 800), () {
          if (mounted && _isVoiceMode) _startListening();
        });
      }
    };

    final onError = (String e) {
      if (!mounted) return;
      setState(() {
        _aiResponseText = 'Could not connect. Is the backend running?';
        _voiceState = VoiceState.idle;
      });
    };

    if (useOnlineGemini && geminiApiKey.isNotEmpty) {
      await _apiService.streamGeminiDirectly(
        message: query,
        apiKey: geminiApiKey,
        chatHistory: history,
        onToken: onToken,
        onDone: onDone,
        onError: onError,
      );
    } else {
      await _apiService.streamCompanionResponse(
        message: query,
        chatHistory: history,
        onToken: onToken,
        onDone: onDone,
        onError: onError,
      );
    }
  }

  void _enqueueSentence(String sentence) {
    _pendingSentences.add(sentence);
    if (!_ttsActive) _processTtsQueue();
  }

  Future<void> _processTtsQueue() async {
    if (_pendingSentences.isEmpty || !_isVoiceMode) {
      _ttsActive = false;
      return;
    }
    _ttsActive = true;
    setState(() => _voiceState = VoiceState.speaking);

    try {
      while (_pendingSentences.isNotEmpty && _isVoiceMode) {
        final sentence = _pendingSentences.removeAt(0);
        final audio = await _apiService.synthesizeSpeech(sentence, 'auto');
        if (!_isVoiceMode) break;
        if (audio != null) {
          await _audioPlayer.play(BytesSource(audio));
          await _audioPlayer.onPlayerComplete.first.timeout(const Duration(seconds: 30));
        } else {
          await Future.delayed(Duration(milliseconds: sentence.length * 55));
        }
      }
    } catch (_) {
      // Always fall through to re-listen even if TTS throws
    }

    _ttsActive = false;
    await _playUiTone(start: false);
    if (mounted && _isVoiceMode) _startListening();
  }

  // ── Text chat send ────────────────────────────────────────────────
  void _sendMessage() {
    if (_controller.text.trim().isEmpty) return;
    Provider.of<ChatProvider>(context, listen: false)
        .sendMessage(_controller.text);
    _controller.clear();
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  void _toggleVoiceMode() {
    if (!_isVoiceMode) {
      FocusScope.of(context).unfocus();
      _pendingSentences.clear();
      _sentenceAccumulator = '';
      _ttsActive = false;
      if (_speechEnabled) _startListening();
    } else {
      _audioRecorder.stop();
      _audioPlayer.stop();
      _pendingSentences.clear();
    }
    setState(() => _isVoiceMode = !_isVoiceMode);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _amplitudeSub?.cancel();
    _audioRecorder.stop();
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    _tonePlayer.dispose();
    super.dispose();
  }

  // ── Build ─────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      final isTablet = constraints.maxWidth >= 800;
      return Scaffold(
        backgroundColor: Colors.white,
        appBar: _isVoiceMode
            ? null
            : AppBar(
                backgroundColor: Colors.white,
                elevation: 0,
                surfaceTintColor: Colors.transparent,
                centerTitle: true,
                title: Text(
                  'Health Wellness Companion',
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w500,
                    color: const Color(0xFF1F2937),
                    fontSize: 16,
                    letterSpacing: -0.3,
                  ),
                ),
                actions: [
                  Padding(
                    padding: const EdgeInsets.only(right: 16),
                    child: CircleAvatar(
                      radius: 16,
                      backgroundColor: const Color(0xFFE5E7EB),
                      child: Text('W',
                          style: GoogleFonts.inter(
                              fontWeight: FontWeight.w700,
                              fontSize: 13,
                              color: const Color(0xFF374151))),
                    ),
                  ),
                ],
                bottom: PreferredSize(
                  preferredSize: const Size.fromHeight(1),
                  child: Container(color: const Color(0xFFF3F4F6), height: 1),
                ),
              ),
        drawer: isTablet ? null : Drawer(child: _buildSidebar()),
        body: Row(
          children: [
            if (isTablet)
              Container(
                width: 260,
                decoration: const BoxDecoration(
                  color: Color(0xFFF9FAFB),
                  border: Border(right: BorderSide(color: Color(0xFFE5E7EB))),
                ),
                child: _buildSidebar(),
              ),
            Expanded(child: _buildMainChatArea()),
          ],
        ),
      );
    });
  }

  Widget _buildSidebar() {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: InkWell(
              onTap: () {
                Provider.of<ChatProvider>(context, listen: false).clearChat();
                final scaffold = Scaffold.maybeOf(context);
                if (scaffold != null && scaffold.isDrawerOpen) {
                  Navigator.pop(context);
                }
              },
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                decoration: BoxDecoration(
                  border: Border.all(color: const Color(0xFFE5E7EB)),
                  borderRadius: BorderRadius.circular(8),
                  color: Colors.white,
                ),
                child: Row(
                  children: [
                    const Icon(Icons.add, color: Color(0xFF374151), size: 20),
                    const SizedBox(width: 8),
                    Text('New Chat',
                        style: GoogleFonts.inter(
                            color: const Color(0xFF374151),
                            fontWeight: FontWeight.w500,
                            fontSize: 14)),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text('Recent',
                style: GoogleFonts.inter(
                    color: const Color(0xFF9CA3AF),
                    fontSize: 12,
                    fontWeight: FontWeight.w600)),
          ),
          Expanded(
            child: Consumer<ChatProvider>(
              builder: (_, provider, __) {
                final msgs = provider.messages
                    .where((m) => m.isUser)
                    .toList()
                    .reversed
                    .take(6)
                    .toList();
                return ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  children: msgs
                      .map((m) => _buildHistoryItem(m.text))
                      .toList(),
                );
              },
            ),
          ),
          const Divider(height: 1, color: Color(0xFFF3F4F6)),
          ListTile(
            leading:
                const Icon(Icons.tune, color: Color(0xFF374151)),
            title: Text('Settings',
                style: GoogleFonts.inter(
                    color: const Color(0xFF374151),
                    fontWeight: FontWeight.w500,
                    fontSize: 14)),
            onTap: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => SettingsScreen())),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryItem(String title) {
    return ListTile(
      dense: true,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      title: Text(title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: GoogleFonts.inter(
              color: const Color(0xFF4B5563), fontSize: 14)),
      onTap: () {},
    );
  }

  Widget _buildMainChatArea() {
    final chatProvider = Provider.of<ChatProvider>(context);
    return Stack(
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.only(
                  top: 24, bottom: 100, left: 16, right: 16),
              itemCount: chatProvider.messages.length,
              itemBuilder: (_, i) =>
                  _buildMessageRow(chatProvider.messages[i]),
            ),
          ),
        ),
        if (chatProvider.isLoading && !_isVoiceMode)
          Positioned(
            bottom: 90,
            left: 0,
            right: 0,
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                        color: Colors.black.withValues(alpha: 0.05),
                        blurRadius: 10,
                        offset: const Offset(0, 4))
                  ],
                  border:
                      Border.all(color: const Color(0xFFF3F4F6)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                            Color(0xFF374151)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text('Thinking...',
                        style: GoogleFonts.inter(
                            color: const Color(0xFF6B7280), fontSize: 13)),
                  ],
                ),
              ),
            ),
          ),
        if (!_isVoiceMode)
          Align(
              alignment: Alignment.bottomCenter,
              child: _buildFloatingInputArea()),
        if (_isVoiceMode) _buildVoiceOverlay(),
      ],
    );
  }

  Widget _buildMessageRow(ChatMessage msg) {
    return TweenAnimationBuilder<double>(
      key: ValueKey(msg.hashCode),
      tween: Tween(begin: 0.0, end: 1.0),
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOutCubic,
      builder: (_, value, child) => Transform.translate(
        offset: Offset(0, (1 - value) * 10),
        child: Opacity(opacity: value, child: child),
      ),
      child: Padding(
        padding: const EdgeInsets.only(bottom: 24),
        child: msg.isUser ? _buildUserBubble(msg) : _buildAIBubble(msg),
      ),
    );
  }

  Widget _buildUserBubble(ChatMessage msg) {
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.only(left: 60),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        decoration: BoxDecoration(
          color: const Color(0xFF00A86B),
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomLeft: Radius.circular(20),
            bottomRight: Radius.circular(4),
          ),
          boxShadow: [
            BoxShadow(
                color: const Color(0xFF00A86B).withValues(alpha: 0.15),
                blurRadius: 8,
                offset: const Offset(0, 4))
          ],
        ),
        child: Text(msg.text,
            style: GoogleFonts.inter(
                color: Colors.white, fontSize: 15, height: 1.4)),
      ),
    );
  }

  Widget _buildAIBubble(ChatMessage msg) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: CircleAvatar(
              radius: 14,
              backgroundColor: const Color(0xFFF3F4F6),
              child: Text('S',
                  style: GoogleFonts.lora(
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                      color: const Color(0xFF374151))),
            ),
          ),
          Flexible(
            child: Container(
              margin: const EdgeInsets.only(right: 40),
              padding:
                  const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: const BoxDecoration(
                color: Color(0xFFF1F2F6),
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(20),
                  topRight: Radius.circular(20),
                  bottomRight: Radius.circular(20),
                  bottomLeft: Radius.circular(4),
                ),
              ),
              child: MarkdownBody(
                data: msg.text,
                styleSheet: MarkdownStyleSheet(
                  p: GoogleFonts.inter(
                      color: const Color(0xFF1F2937),
                      fontSize: 15,
                      height: 1.5),
                  strong: GoogleFonts.inter(
                      color: const Color(0xFF1F2937),
                      fontSize: 15,
                      fontWeight: FontWeight.w600),
                  code: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 13,
                      backgroundColor: Color(0xFFE5E7EB)),
                  blockquote: GoogleFonts.inter(
                      color: const Color(0xFF6B7280), fontSize: 14),
                ),
                shrinkWrap: true,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFloatingInputArea() {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 800),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: const BoxDecoration(
          color: Colors.white,
          border:
              Border(top: BorderSide(color: Color(0xFFF3F4F6))),
        ),
        child: SafeArea(
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Row(
              children: [
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.add,
                      color: Color(0xFF9CA3AF), size: 24),
                  onPressed: () {},
                ),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    style: GoogleFonts.inter(
                        color: const Color(0xFF1F2937), fontSize: 15),
                    decoration: InputDecoration(
                      hintText: 'Message Sehat Saathi...',
                      hintStyle: GoogleFonts.inter(
                          color: const Color(0xFF9CA3AF), fontSize: 15),
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding:
                          const EdgeInsets.symmetric(vertical: 12),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                ValueListenableBuilder<TextEditingValue>(
                  valueListenable: _controller,
                  builder: (_, value, __) => value.text.isEmpty
                      ? IconButton(
                          icon: const Icon(Icons.mic,
                              color: Color(0xFF6B7280)),
                          onPressed: _toggleVoiceMode,
                        )
                      : IconButton(
                          icon: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: const BoxDecoration(
                              color: Color(0xFF00A86B),
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(Icons.arrow_upward,
                                color: Colors.white, size: 16),
                          ),
                          onPressed: _sendMessage,
                        ),
                ),
                const SizedBox(width: 4),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── Interrupt: tap orb while speaking → stop TTS → listen again ──
  void _interruptSpeaking() {
    if (_voiceState != VoiceState.speaking) return;
    _audioPlayer.stop();
    _pendingSentences.clear();
    _ttsActive = false;
    _startListening();
  }

  // ── Voice overlay — dark immersive, no buttons except close ─────
  Widget _buildVoiceOverlay() {
    return Positioned.fill(
      child: GestureDetector(
        // swipe down to close
        onVerticalDragEnd: (d) {
          if (d.primaryVelocity != null && d.primaryVelocity! > 300) {
            _toggleVoiceMode();
          }
        },
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Color(0xFF050510), Color(0xFF0A0A1A), Color(0xFF0D0D20)],
            ),
          ),
          child: SafeArea(
            child: Column(
              children: [
                // ── top: subtle close only ─────────────────────
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      GestureDetector(
                        onTap: _toggleVoiceMode,
                        child: Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.08),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.close,
                              color: Colors.white54, size: 18),
                        ),
                      ),
                    ],
                  ),
                ),

                const Spacer(flex: 2),

                // ── transcript above orb (listening) ──────────
                if (_voiceState == VoiceState.listening)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(32, 0, 32, 28),
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 200),
                      child: Text(
                        _recognizedWords.isEmpty
                            ? 'Listening...'
                            : _recognizedWords,
                        key: ValueKey(_recognizedWords),
                        textAlign: TextAlign.center,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(
                          color: _recognizedWords.isEmpty
                              ? Colors.white30
                              : Colors.white.withValues(alpha: 0.9),
                          fontSize: _recognizedWords.isEmpty ? 16 : 20,
                          fontWeight: _recognizedWords.isEmpty
                              ? FontWeight.w300
                              : FontWeight.w500,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ),

                // ── orb — tap to interrupt while speaking ──────
                GestureDetector(
                  onTap: _voiceState == VoiceState.speaking
                      ? _interruptSpeaking
                      : null,
                  child: _buildOrb(),
                ),

                const SizedBox(height: 36),

                // ── P2: waveform below orb ─────────────────────
                SizedBox(height: 52, child: _buildWaveform()),

                const SizedBox(height: 28),

                // ── AI response text (speaking/processing) ─────
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 36),
                  child: _buildResponseText(),
                ),

                const Spacer(flex: 3),

                // ── bottom hint — swipe or tap to interrupt ────
                Padding(
                  padding: const EdgeInsets.only(bottom: 24),
                  child: Text(
                    _voiceState == VoiceState.speaking
                        ? 'Tap orb to interrupt'
                        : _voiceState == VoiceState.listening
                            ? 'Swipe down to close'
                            : '',
                    style: GoogleFonts.inter(
                        color: Colors.white24,
                        fontSize: 12,
                        letterSpacing: 0.3),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildResponseText() {
    if (_voiceState == VoiceState.processing) {
      return _buildThinkingDots();
    }
    if (_voiceState == VoiceState.speaking && _aiResponseText.isNotEmpty) {
      return Text(
        _aiResponseText,
        textAlign: TextAlign.center,
        maxLines: 4,
        overflow: TextOverflow.ellipsis,
        style: GoogleFonts.inter(
          color: Colors.white.withValues(alpha: 0.75),
          fontSize: 17,
          fontWeight: FontWeight.w400,
          height: 1.5,
        ),
      );
    }
    return const SizedBox.shrink();
  }

  Widget _buildThinkingDots() {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (_, __) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(3, (i) {
            final phase = _pulseController.value * math.pi * 2 - i * 0.6;
            final scale = 0.6 + math.sin(phase).abs() * 0.4;
            return Transform.scale(
              scale: scale,
              child: Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: const BoxDecoration(
                    color: Colors.white54, shape: BoxShape.circle),
              ),
            );
          }),
        );
      },
    );
  }

  Widget _buildOrb() {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (_, __) {
        // Real mic amplitude drives orb scale
        double ampScale = 0.0;
        if (_voiceState == VoiceState.listening) {
          ampScale = (_soundLevel / 10.0).clamp(0.0, 1.0) * 0.18;
        } else if (_voiceState == VoiceState.speaking) {
          ampScale =
              math.sin(_pulseController.value * math.pi * 2).abs() * 0.14;
        } else if (_voiceState == VoiceState.processing) {
          ampScale =
              math.sin(_pulseController.value * math.pi * 3).abs() * 0.05;
        }

        // Color shifts per state
        final List<Color> orbColors = _voiceState == VoiceState.speaking
            ? const [
                Color(0xFF60A5FA), // blue
                Color(0xFF818CF8), // indigo
                Color(0xFFA78BFA), // violet
                Color(0xFF34D399), // teal
              ]
            : _voiceState == VoiceState.processing
                ? const [
                    Color(0xFFFBBF24), // amber
                    Color(0xFFF97316), // orange
                    Color(0xFF34D399), // teal
                    Color(0xFF60A5FA), // blue
                  ]
                : const [
                    Color(0xFF34D399), // emerald
                    Color(0xFF10B981), // green
                    Color(0xFF059669), // dark green
                    Color(0xFF60A5FA), // blue accent
                  ];

        // Rotating gradient offset for swirling effect
        final t = _pulseController.value;
        final sweep = t * math.pi * 2;

        return Transform.scale(
          scale: 1.0 + ampScale,
          child: Container(
            width: 220,
            height: 220,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                // outer glow
                BoxShadow(
                  color: orbColors[0].withValues(alpha: (0.35 + ampScale * 0.4).clamp(0.0, 1.0)),
                  blurRadius: 60 + ampScale * 40,
                  spreadRadius: 4 + ampScale * 12,
                ),
                BoxShadow(
                  color: orbColors[2].withValues(alpha: 0.15),
                  blurRadius: 100,
                  spreadRadius: 16,
                ),
              ],
            ),
            child: CustomPaint(
              painter: _OrbPainter(
                colors: orbColors,
                sweep: sweep,
                amplitude: ampScale,
              ),
            ),
          ),
        );
      },
    );
  }

  // ── P2: Waveform — real mic levels while listening, sine while speaking ──
  Widget _buildWaveform() {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (_, __) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: List.generate(40, (i) {
            double barHeight;

            if (_voiceState == VoiceState.listening) {
              final bufIdx = (_waveformWriteIdx + i) % 35;
              final level = _waveformBuffer[bufIdx];
              final edgeFade = 1.0 - ((i - 20).abs() / 20.0) * 0.5;
              barHeight =
                  (4.0 + (level / 10.0).clamp(0.0, 1.0) * 42.0) * edgeFade;
            } else if (_voiceState == VoiceState.speaking) {
              final phase = (i / 40.0) * math.pi * 5;
              final sine =
                  math.sin(phase + _pulseController.value * math.pi * 2);
              barHeight = 4 + sine.abs() * 36;
            } else if (_voiceState == VoiceState.processing) {
              final phase = (i / 40.0) * math.pi * 4;
              final sine =
                  math.sin(phase + _pulseController.value * math.pi * 2);
              barHeight = 3 + sine.abs() * 6;
            } else {
              barHeight = 3;
            }

            // Edge fade
            double opacity = 1.0;
            if (i < 8) opacity = i / 8.0;
            if (i > 32) opacity = (40 - i) / 8.0;

            // Color shifts per state
            final barColor = _voiceState == VoiceState.speaking
                ? Color.lerp(const Color(0xFF818CF8), const Color(0xFF34D399),
                    i / 40.0)!
                : _voiceState == VoiceState.processing
                    ? const Color(0xFFFBBF24)
                    : const Color(0xFF34D399);

            return Container(
              width: 3,
              height: barHeight.clamp(3.0, 48.0),
              margin: const EdgeInsets.symmetric(horizontal: 1.5),
              decoration: BoxDecoration(
                color: barColor.withValues(alpha: (opacity * 0.9).clamp(0.0, 1.0)),
                borderRadius: BorderRadius.circular(2),
              ),
            );
          }),
        );
      },
    );
  }
}

// ── Orb custom painter: swirling multi-color fluid blob ──────────────
class _OrbPainter extends CustomPainter {
  final List<Color> colors;
  final double sweep;
  final double amplitude;

  _OrbPainter({
    required this.colors,
    required this.sweep,
    required this.amplitude,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = cx;

    // Base circle
    final basePaint = Paint()
      ..shader = RadialGradient(
        center: Alignment(
          math.cos(sweep) * 0.25,
          math.sin(sweep) * 0.25,
        ),
        radius: 1.0,
        colors: colors,
        stops: const [0.0, 0.35, 0.7, 1.0],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r));

    canvas.drawCircle(Offset(cx, cy), r, basePaint);

    // Specular highlight
    final highlightPaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.45, -0.5),
        radius: 0.6,
        colors: [
          Colors.white.withValues(alpha: 0.35),
          Colors.white.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r));
    canvas.drawCircle(Offset(cx, cy), r, highlightPaint);

    // Animated color blobs for swirling effect
    for (int i = 0; i < colors.length; i++) {
      final angle = sweep + (i * math.pi / 2);
      final bx = cx + math.cos(angle) * r * 0.38;
      final by = cy + math.sin(angle) * r * 0.38;
      final blobPaint = Paint()
        ..color = colors[i].withValues(alpha: (0.22 + amplitude * 0.2).clamp(0.0, 1.0))
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 28);
      canvas.drawCircle(Offset(bx, by), r * 0.52, blobPaint);
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.sweep != sweep || old.amplitude != amplitude;
}
