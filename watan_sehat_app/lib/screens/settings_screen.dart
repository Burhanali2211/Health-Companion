import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';
import 'dart:io';
import '../services/api_service.dart';
import '../services/model_manager_service.dart';
import 'model_download_screen.dart';

class SettingsScreen extends StatefulWidget {
  @override
  _SettingsScreenState createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen>
    with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  late TabController _tabController;

  // Models state
  List<Map<String, dynamic>> _models = [];
  String _activeModel = '';
  bool _modelsLoading = true;
  String? _modelError;

  // RAG state
  bool _ragEnabled = true;
  int _ragChunks = 0;
  String _ragSizeLabel = '...';
  bool _ragLoading = true;
  bool _ragRebuilding = false;
  String? _ragError;

  // Settings state
  double _temperature = 0.7;
  int _maxTokens = 200;
  String _language = 'auto';
  String _ageMode = 'jawaan';
  String _district = 'srinagar';
  double _voiceSpeed = 1.0;
  bool _settingsLoading = true;
  bool _settingsSaving = false;

  // Server URL (configurable for real-device LAN access)
  final TextEditingController _serverUrlCtrl = TextEditingController();
  final TextEditingController _newGeminiApiKeyCtrl = TextEditingController();
  List<String> _geminiApiKeys = [];
  String _activeGeminiApiKey = '';
  bool _useOnlineGemini = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _serverUrlCtrl.text = ApiService.baseUrl;
    _loadAll();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _serverUrlCtrl.dispose();
    _newGeminiApiKeyCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    await Future.wait([_loadModels(), _loadRag(), _loadSettings()]);
  }

  Future<void> _loadModels() async {
    setState(() { _modelsLoading = true; _modelError = null; });
    final res = await _api.getModels();
    if (mounted) {
      setState(() {
        _modelsLoading = false;
        if (res['status'] == 'ok') {
          final data = res['data'] as Map<String, dynamic>;
          _models = List<Map<String, dynamic>>.from(data['models'] ?? []);
          _activeModel = data['active_model'] ?? '';
        } else {
          _modelError = res['message'] ?? 'Could not reach backend';
        }
      });
    }
  }

  Future<void> _loadRag() async {
    setState(() { _ragLoading = true; _ragError = null; });
    final res = await _api.getRagStatus();
    if (mounted) {
      setState(() {
        _ragLoading = false;
        if (res['status'] == 'ok') {
          final d = res['data'] as Map<String, dynamic>;
          _ragChunks = d['chunk_count'] ?? 0;
          _ragSizeLabel = d['size_label'] ?? '0 MB';
        } else {
          _ragError = res['message'] ?? 'Could not reach backend';
        }
      });
    }
  }

  Future<void> _loadSettings() async {
    setState(() { _settingsLoading = true; });
    final prefs = await SharedPreferences.getInstance();
    _geminiApiKeys = prefs.getStringList('gemini_api_keys') ?? [];
    _activeGeminiApiKey = prefs.getString('active_gemini_api_key') ?? '';
    _useOnlineGemini = prefs.getBool('use_online_gemini') ?? false;
    
    if (_activeGeminiApiKey.isEmpty && _geminiApiKeys.isNotEmpty) {
      _activeGeminiApiKey = _geminiApiKeys.first;
    }

    final res = await _api.getSettings();
    if (mounted) {
      setState(() {
        _settingsLoading = false;
        if (res['status'] == 'ok') {
          final d = res['data'] as Map<String, dynamic>;
          _temperature = (d['temperature'] as num?)?.toDouble() ?? 0.7;
          _maxTokens = (d['max_tokens'] as num?)?.toInt() ?? 200;
          _language = d['language'] ?? 'auto';
          _ageMode = d['age_mode'] ?? 'jawaan';
          _district = d['district'] ?? 'srinagar';
          _voiceSpeed = (d['voice_speed'] as num?)?.toDouble() ?? 1.0;
        }
      });
    }
  }

  Future<void> _saveSettings() async {
    setState(() => _settingsSaving = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('use_online_gemini', _useOnlineGemini);
    await prefs.setStringList('gemini_api_keys', _geminiApiKeys);
    await prefs.setString('active_gemini_api_key', _activeGeminiApiKey);
    
    // Persist server URL first so subsequent API calls use the new URL
    await ApiService.setServerUrl(_serverUrlCtrl.text);
    final ok = await _api.updateSettings({
      'temperature': _temperature,
      'max_tokens': _maxTokens,
      'language': _language,
      'age_mode': _ageMode,
      'district': _district,
      'voice_speed': _voiceSpeed,
    });
    if (mounted) {
      setState(() => _settingsSaving = false);
      _showSnack(ok ? 'Settings saved' : 'Server URL and Gemini settings saved (backend offline)', true);
    }
  }

  void _addGeminiKey(String key) async {
    key = key.trim();
    if (key.isEmpty) return;
    if (_geminiApiKeys.contains(key)) {
      _showSnack('Key already exists in the list', false);
      return;
    }
    setState(() {
      _geminiApiKeys.add(key);
      if (_activeGeminiApiKey.isEmpty) {
        _activeGeminiApiKey = key;
      }
      _newGeminiApiKeyCtrl.clear();
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('gemini_api_keys', _geminiApiKeys);
    await prefs.setString('active_gemini_api_key', _activeGeminiApiKey);
    _showSnack('API Key added', true);
  }

  void _deleteGeminiKey(String key) async {
    setState(() {
      _geminiApiKeys.remove(key);
      if (_activeGeminiApiKey == key) {
        _activeGeminiApiKey = _geminiApiKeys.isNotEmpty ? _geminiApiKeys.first : '';
      }
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('gemini_api_keys', _geminiApiKeys);
    await prefs.setString('active_gemini_api_key', _activeGeminiApiKey);
    _showSnack('API Key removed', true);
  }

  void _selectGeminiKey(String key) async {
    setState(() {
      _activeGeminiApiKey = key;
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('active_gemini_api_key', _activeGeminiApiKey);
    _showSnack('Active API Key updated', true);
  }

  Future<void> _setActiveModel(String name) async {
    final ok = await _api.setActiveModel(name);
    if (mounted) {
      if (ok) {
        setState(() => _activeModel = name);
        _showSnack('Active model → $name', true);
      } else {
        _showSnack('Failed to switch model', false);
      }
    }
  }

  Future<void> _deleteModel(String name) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delete model?', style: GoogleFonts.inter()),
        content: Text('Remove $name from Ollama?', style: GoogleFonts.inter()),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    final ok = await _api.deleteModel(name);
    if (mounted) {
      if (ok) {
        _showSnack('Deleted $name', true);
        _loadModels();
      } else {
        _showSnack('Delete failed', false);
      }
    }
  }

  Future<void> _toggleRag(bool val) async {
    setState(() => _ragEnabled = val);
    final ok = await _api.setRagEnabled(val);
    if (!ok && mounted) _showSnack('RAG toggle failed', false);
  }

  Future<void> _rebuildRag() async {
    setState(() => _ragRebuilding = true);
    final ok = await _api.rebuildRag();
    if (mounted) {
      setState(() => _ragRebuilding = false);
      _showSnack(ok ? 'Knowledge base rebuilt' : 'Rebuild failed', ok);
      if (ok) _loadRag();
    }
  }

  void _showSnack(String msg, bool ok) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg, style: GoogleFonts.inter()),
        backgroundColor: ok ? const Color(0xFF00A86B) : Colors.red[700],
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Color(0xFF1F2937), size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        centerTitle: true,
        title: Text(
          'Health Companion',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 18),
        ),
        bottom: TabBar(
          controller: _tabController,
          labelColor: const Color(0xFF00A86B),
          unselectedLabelColor: const Color(0xFF6B7280),
          indicatorColor: const Color(0xFF00A86B),
          labelStyle: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 13),
          unselectedLabelStyle: GoogleFonts.inter(fontWeight: FontWeight.w500, fontSize: 13),
          tabs: const [
            Tab(text: 'Models'),
            Tab(text: 'Knowledge'),
            Tab(text: 'Config'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildModelsTab(),
          _buildKnowledgeTab(),
          _buildConfigTab(),
        ],
      ),
    );
  }

  // ── MODELS TAB ────────────────────────────────────────────────────

  Widget _buildModelsTab() {
    final modelManager = Provider.of<ModelManagerService>(context);

    return RefreshIndicator(
      onRefresh: _loadModels,
      color: const Color(0xFF00A86B),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _sectionLabel('ON-DEVICE OFFLINE AI MODELS'),
          const SizedBox(height: 12),
          ...modelManager.availableModels.map((model) => _buildOnDeviceModelCard(modelManager, model)),
          const SizedBox(height: 28),
          
          if (_modelsLoading) ...[
            const Center(child: CircularProgressIndicator(color: Color(0xFF00A86B))),
            const SizedBox(height: 24),
          ] else if (_modelError == null && _models.isNotEmpty) ...[
            _sectionLabel('LOCAL SERVER MODELS (OLLAMA)'),
            const SizedBox(height: 12),
            ..._models.map((m) => _buildModelCard(m)),
            const SizedBox(height: 24),
            _buildPullCard(),
          ] else if (_modelError != null) ...[
            const Divider(height: 40, color: Color(0xFFF3F4F6)),
            _sectionLabel('OLLAMA BACKEND INTEGRATION (OPTIONAL)'),
            const SizedBox(height: 12),
            _buildOfflineBanner(_modelError!, _loadModels),
          ],
        ],
      ),
    );
  }

  Widget _buildOnDeviceModelCard(ModelManagerService modelManager, LocalModel model) {
    final isDownloading = modelManager.isDownloading[model.id] ?? false;
    final progress = modelManager.downloadProgress[model.id] ?? 0.0;
    final isActive = modelManager.activeModelId == model.id;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: isActive ? Border.all(color: const Color(0xFF00A86B).withOpacity(0.4), width: 2) : null,
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isActive ? const Color(0xFF00A86B).withOpacity(0.1) : const Color(0xFFF3F4F6),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.download_for_offline, color: isActive ? const Color(0xFF00A86B) : const Color(0xFF6B7280), size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(model.name, style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 15)),
                      const SizedBox(height: 2),
                      Text(model.realName, style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF), fontFamily: 'monospace')),
                    ],
                  ),
                ),
                if (isActive)
                  _chip('Active', const Color(0xFF00A86B)),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              model.description,
              style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280)),
            ),
            const SizedBox(height: 6),
            Text(
              'Size: ${model.sizeInMB} MB',
              style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF9CA3AF), fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 14),
            FutureBuilder<bool>(
              future: modelManager.isModelDownloaded(model.id),
              builder: (context, snapshot) {
                final isDownloaded = snapshot.data ?? false;

                if (isDownloading) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      LinearProgressIndicator(
                        value: progress,
                        color: const Color(0xFF00A86B),
                        backgroundColor: const Color(0xFFE5E7EB),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Downloading model to device...', style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF6B7280))),
                          Text('${(progress * 100).toStringAsFixed(1)}%', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: const Color(0xFF00A86B))),
                        ],
                      ),
                    ],
                  );
                }

                if (isDownloaded) {
                  return Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.delete_outline, color: Colors.red, size: 20),
                        tooltip: 'Delete downloaded model file',
                        onPressed: () async {
                          final confirmed = await showDialog<bool>(
                            context: context,
                            builder: (ctx) => AlertDialog(
                              title: Text('Delete model file?', style: GoogleFonts.inter()),
                              content: Text('Remove local copy of ${model.name} (${model.realName}) from device storage?', style: GoogleFonts.inter()),
                              actions: [
                                TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text('Cancel')),
                                TextButton(
                                  onPressed: () => Navigator.pop(ctx, true),
                                  child: Text('Delete', style: TextStyle(color: Colors.red)),
                                ),
                              ],
                            ),
                          );
                          if (confirmed == true) {
                            final path = await modelManager.getModelPath(model.id);
                            final file = File(path);
                            if (await file.exists()) {
                              await file.delete();
                              _showSnack('Deleted local model file', true);
                              setState(() {});
                            }
                          }
                        },
                      ),
                      const SizedBox(width: 8),
                      if (isActive)
                        _chip('Using on device', const Color(0xFF00A86B))
                      else
                        _outlineBtn('Select Model', () async {
                          await modelManager.setActiveModel(model.id);
                          _showSnack('On-device model changed to ${model.name}', true);
                          setState(() {});
                        }),
                    ],
                  );
                }

                return SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.download, size: 18),
                    label: Text('Download to Device', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      backgroundColor: const Color(0xFF00A86B),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    onPressed: () => modelManager.downloadModel(model.id),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  /// Compact offline notice — unlike the old full-screen error, this keeps the
  /// recommended/downloadable models list below it visible and usable.
  Widget _buildOfflineBanner(String msg, VoidCallback retry) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFFDBA74)),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_outlined, size: 22, color: Color(0xFFC2410C)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Backend offline', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF9A3412), fontSize: 13)),
                const SizedBox(height: 2),
                Text(msg, style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFFC2410C))),
              ],
            ),
          ),
          const SizedBox(width: 8),
          TextButton(
            onPressed: retry,
            style: TextButton.styleFrom(foregroundColor: const Color(0xFFC2410C), padding: const EdgeInsets.symmetric(horizontal: 8)),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyModels() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: _cardDecor(),
      child: Column(
        children: [
          const Icon(Icons.memory_outlined, size: 48, color: Color(0xFF9CA3AF)),
          const SizedBox(height: 12),
          Text('No models installed', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF374151))),
          const SizedBox(height: 4),
          Text('Pull a model below to get started', style: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF6B7280))),
        ],
      ),
    );
  }

  Widget _buildModelCard(Map<String, dynamic> model) {
    final name = model['name'] as String? ?? 'unknown';
    final sizeLabel = model['size_label'] as String? ?? 'Unknown';
    final isActive = model['is_active'] as bool? ?? false;
    final digest = model['digest'] as String? ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: isActive ? Border.all(color: const Color(0xFF00A86B).withValues(alpha: 0.4), width: 2) : null,
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isActive ? const Color(0xFF00A86B).withValues(alpha: 0.1) : const Color(0xFFF3F4F6),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.memory, color: isActive ? const Color(0xFF00A86B) : const Color(0xFF6B7280), size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 14)),
                  if (digest.isNotEmpty)
                    Text(digest, style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF), fontFamily: 'monospace')),
                  const SizedBox(height: 2),
                  Text(sizeLabel, style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280))),
                ],
              ),
            ),
            // Ollama hub link
            IconButton(
              icon: const Icon(Icons.open_in_new, size: 16, color: Color(0xFF9CA3AF)),
              onPressed: () => _openModelPage(name),
              tooltip: 'View on Ollama Hub',
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            ),
            const SizedBox(width: 4),
            if (isActive)
              _chip('Active', const Color(0xFF00A86B))
            else
              Row(
                children: [
                  _outlineBtn('Use', () => _setActiveModel(name)),
                  const SizedBox(width: 6),
                  IconButton(
                    icon: const Icon(Icons.delete_outline, size: 18, color: Color(0xFFEF4444)),
                    onPressed: () => _deleteModel(name),
                    tooltip: 'Delete',
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPullCard() {
    final ctrl = TextEditingController();
    bool pulling = false;

    // Recommended for offline, on-device health advice — small enough for
    // Pi/low-RAM hardware, best reasoning-to-size ratio first.
    const recommended = [
      {'name': 'phi3:mini', 'size': '2.2 GB', 'desc': 'Best for health advice — strong reasoning'},
      {'name': 'gemma2:2b', 'size': '1.6 GB', 'desc': 'Balanced quality, good for symptoms Q&A'},
      {'name': 'qwen2.5:1.5b', 'size': '1.0 GB', 'desc': 'Fast & multilingual (Urdu/Koshur)'},
      {'name': 'llama3.2:1b', 'size': '1.3 GB', 'desc': 'Very fast, lighter hardware'},
      {'name': 'tinyllama:1.1b', 'size': '0.6 GB', 'desc': 'Smallest, fastest, lowest RAM'},
    ];

    return StatefulBuilder(builder: (ctx, ss) {
      return Container(
        decoration: _cardDecor(),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Recommended Models', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 15)),
              const SizedBox(height: 4),
              Text(
                _modelError != null
                    ? 'Connect to the backend to download — once installed these run fully offline'
                    : 'Download runs in background via Ollama, then works fully offline',
                style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280)),
              ),
              const SizedBox(height: 12),
              // Quick chips
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: recommended.map((m) {
                  return Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFFF0FFF4),
                      border: Border.all(color: const Color(0xFF00A86B).withValues(alpha: 0.4)),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        GestureDetector(
                          onTap: () => ss(() => ctrl.text = m['name']!),
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(10, 6, 6, 6),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(m['name']!, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: const Color(0xFF065F46))),
                                Text('${m['size']} · ${m['desc']}', style: GoogleFonts.inter(fontSize: 10, color: const Color(0xFF6B7280))),
                              ],
                            ),
                          ),
                        ),
                        // Link to Ollama model page
                        GestureDetector(
                          onTap: () => _openModelPage(m['name']!),
                          child: Container(
                            padding: const EdgeInsets.fromLTRB(0, 6, 8, 6),
                            child: const Icon(Icons.open_in_new, size: 14, color: Color(0xFF00A86B)),
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: ctrl,
                      style: GoogleFonts.inter(fontSize: 14),
                      decoration: InputDecoration(
                        hintText: 'model:tag',
                        hintStyle: GoogleFonts.inter(color: const Color(0xFF9CA3AF)),
                        filled: true,
                        fillColor: const Color(0xFFF3F4F6),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: (pulling || _modelError != null) ? null : () async {
                      final name = ctrl.text.trim();
                      if (name.isEmpty) return;
                      ss(() => pulling = true);
                      _showSnack('Pulling $name… (may take minutes)', true);
                      final ok = await _api.pullModel(name);
                      ss(() => pulling = false);
                      if (ok) {
                        _showSnack('$name pulled successfully', true);
                        _loadModels();
                      } else {
                        _showSnack('Pull failed — check Ollama is running', false);
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1F2937),
                      disabledBackgroundColor: const Color(0xFF9CA3AF),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                    child: pulling
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : Text('Pull', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    });
  }


  // ── KNOWLEDGE TAB ─────────────────────────────────────────────────

  Widget _buildKnowledgeTab() {
    if (_ragLoading) {
      return const Center(child: CircularProgressIndicator(color: Color(0xFF00A86B)));
    }
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _sectionLabel('RETRIEVAL-AUGMENTED GENERATION'),
        const SizedBox(height: 12),
        Container(
          decoration: _cardDecor(),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Enable RAG', style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 15)),
                          const SizedBox(height: 4),
                          Text('Grounds AI in Kashmiri medical data', style: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF6B7280))),
                        ],
                      ),
                    ),
                    Switch(value: _ragEnabled, activeThumbColor: const Color(0xFF00A86B), onChanged: _toggleRag),
                  ],
                ),
                if (_ragError != null) ...[
                  const SizedBox(height: 12),
                  Text(_ragError!, style: GoogleFonts.inter(color: Colors.red, fontSize: 12)),
                ] else ...[
                  const Divider(height: 28, color: Color(0xFFF3F4F6)),
                  _statRow(Icons.description_outlined, 'Knowledge chunks', '$_ragChunks indexed'),
                  const SizedBox(height: 10),
                  _statRow(Icons.storage_outlined, 'Data size', _ragSizeLabel),
                  const SizedBox(height: 10),
                  _statRow(Icons.layers_outlined, 'TF-IDF index', 'In-memory, 4 age modes'),
                ],
                const Divider(height: 28, color: Color(0xFFF3F4F6)),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _ragRebuilding ? null : _rebuildRag,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1F2937),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    icon: _ragRebuilding
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.refresh, color: Colors.white, size: 18),
                    label: Text(
                      _ragRebuilding ? 'Rebuilding…' : 'Rebuild Knowledge Base',
                      style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        _sectionLabel('DATA SOURCES'),
        const SizedBox(height: 12),
        _buildSourceFile('diet_plans.json', 'Kashmiri seasonal diet plans × 3 age modes'),
        _buildSourceFile('exercises.json', 'Exercise library × season × indoor/outdoor'),
        _buildSourceFile('seasons.json', '8 Kashmir seasons + health context'),
        _buildSourceFile('kashmir_general.json', 'General Kashmir health knowledge'),
        _buildSourceFile('knowledge/*.json', 'Medication safety, triage, QA pairs'),
      ],
    );
  }

  Widget _buildSourceFile(String name, String desc) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: _cardDecor(),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            const Icon(Icons.insert_drive_file_outlined, size: 18, color: Color(0xFF00A86B)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Color(0xFF1F2937), fontFamily: 'monospace')),
                  Text(desc, style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── CONFIG TAB ───────────────────────────────────────────────────

  Widget _buildConfigTab() {
    if (_settingsLoading) {
      return const Center(child: CircularProgressIndicator(color: Color(0xFF00A86B)));
    }
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _sectionLabel('MODEL INFERENCE'),
        const SizedBox(height: 12),
        Container(
          decoration: _cardDecor(),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _sliderRow(
                  label: 'Temperature',
                  value: _temperature,
                  min: 0.1,
                  max: 1.0,
                  divisions: 9,
                  display: _temperature.toStringAsFixed(1),
                  hint: 'Lower = focused, Higher = creative',
                  onChanged: (v) => setState(() => _temperature = double.parse(v.toStringAsFixed(1))),
                ),
                const Divider(height: 28, color: Color(0xFFF3F4F6)),
                _sliderRow(
                  label: 'Max Tokens',
                  value: _maxTokens.toDouble(),
                  min: 50,
                  max: 500,
                  divisions: 9,
                  display: '$_maxTokens',
                  hint: 'Response length cap',
                  onChanged: (v) => setState(() => _maxTokens = v.round()),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        _sectionLabel('LANGUAGE & LOCALE'),
        const SizedBox(height: 12),
        Container(
          decoration: _cardDecor(),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _dropdownRow(
                  label: 'Response Language',
                  value: _language,
                  items: const {'auto': 'Auto-detect', 'ur': 'Urdu (اردو)', 'en': 'English', 'ks': 'Koshur (کٲشُر)'},
                  onChanged: (v) => setState(() => _language = v!),
                ),
                const Divider(height: 24, color: Color(0xFFF3F4F6)),
                _dropdownRow(
                  label: 'Default Age Mode',
                  value: _ageMode,
                  items: const {'bacha': 'Bacha (بچہ) — Child', 'jawaan': 'Jawaan (جوان) — Adult', 'buzurg': 'Buzurg (بزرگ) — Elder'},
                  onChanged: (v) => setState(() => _ageMode = v!),
                ),
                const Divider(height: 24, color: Color(0xFFF3F4F6)),
                _dropdownRow(
                  label: 'District',
                  value: _district,
                  items: const {
                    'srinagar': 'Srinagar', 'baramulla': 'Baramulla', 'kupwara': 'Kupwara',
                    'anantnag': 'Anantnag', 'pulwama': 'Pulwama', 'kulgam': 'Kulgam',
                    'ganderbal': 'Ganderbal', 'budgam': 'Budgam', 'bandipora': 'Bandipora',
                    'shopian': 'Shopian',
                  },
                  onChanged: (v) => setState(() => _district = v!),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        _sectionLabel('VOICE'),
        const SizedBox(height: 12),
        Container(
          decoration: _cardDecor(),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: _sliderRow(
              label: 'TTS Speed',
              value: _voiceSpeed,
              min: 0.5,
              max: 1.5,
              divisions: 5,
              display: '${_voiceSpeed.toStringAsFixed(1)}x',
              hint: 'Buzurg mode uses 0.85x automatically',
              onChanged: (v) => setState(() => _voiceSpeed = double.parse(v.toStringAsFixed(1))),
            ),
          ),
        ),
        const SizedBox(height: 20),
        _sectionLabel('BACKEND SERVER'),
        const SizedBox(height: 12),
        Container(
          decoration: _cardDecor(),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Server URL', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: const Color(0xFF1F2937))),
                const SizedBox(height: 4),
                Text('Use 10.0.2.2:8000 for emulator · your LAN IP for real device\ne.g. http://192.168.1.5:8000', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280))),
                const SizedBox(height: 12),
                TextField(
                  controller: _serverUrlCtrl,
                  style: GoogleFonts.inter(fontSize: 13),
                  keyboardType: TextInputType.url,
                  decoration: InputDecoration(
                    hintText: 'http://10.0.2.2:8000',
                    hintStyle: GoogleFonts.inter(color: const Color(0xFF9CA3AF), fontSize: 13),
                    filled: true,
                    fillColor: const Color(0xFFF3F4F6),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    prefixIcon: const Icon(Icons.link, size: 18, color: Color(0xFF6B7280)),
                  ),
                ),
                const SizedBox(height: 12),
                // Quick presets
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _urlPreset('Emulator', 'http://10.0.2.2:8000'),
                    _urlPreset('Localhost', 'http://localhost:8000'),
                    _urlPreset('192.168.1.x', 'http://192.168.1.'),
                    _urlPreset('10.0.0.x', 'http://10.0.0.'),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 20),
        _sectionLabel('GEMINI CLOUD FALLBACK'),
        const SizedBox(height: 12),
        Container(
          decoration: _cardDecor(),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Use Online Gemini', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: const Color(0xFF1F2937))),
                          const SizedBox(height: 2),
                          Text('Direct connection to Gemini API if offline local AI fails or backend is unreachable.', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280))),
                        ],
                      ),
                    ),
                    Switch(
                      value: _useOnlineGemini,
                      activeColor: const Color(0xFF00A86B),
                      onChanged: (v) => setState(() => _useOnlineGemini = v),
                    ),
                  ],
                ),
                const Divider(height: 28, color: Color(0xFFF3F4F6)),
                Text('Add Gemini API Key', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: const Color(0xFF1F2937))),
                const SizedBox(height: 4),
                Text('Add your Google AI Studio Gemini API keys manually below.', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF6B7280))),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _newGeminiApiKeyCtrl,
                        obscureText: true,
                        style: GoogleFonts.inter(fontSize: 13),
                        decoration: InputDecoration(
                          hintText: 'Enter API Key (AIzaSy...)',
                          hintStyle: GoogleFonts.inter(color: const Color(0xFF9CA3AF), fontSize: 13),
                          filled: true,
                          fillColor: const Color(0xFFF3F4F6),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          prefixIcon: const Icon(Icons.vpn_key, size: 18, color: Color(0xFF6B7280)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () => _addGeminiKey(_newGeminiApiKeyCtrl.text),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00A86B),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      ),
                      child: Text('Add', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                if (_geminiApiKeys.isNotEmpty) ...[
                  const Divider(height: 28, color: Color(0xFFF3F4F6)),
                  Text('Saved API Keys', style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14, color: const Color(0xFF1F2937))),
                  const SizedBox(height: 12),
                  ..._geminiApiKeys.map((key) {
                    final isActive = _activeGeminiApiKey == key;
                    final maskedKey = key.length > 12 
                        ? '${key.substring(0, 8)}...${key.substring(key.length - 4)}'
                        : key;
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: isActive ? const Color(0xFFF0FFF4) : const Color(0xFFF9FAFB),
                        border: Border.all(
                          color: isActive ? const Color(0xFF00A86B).withOpacity(0.4) : const Color(0xFFE5E7EB),
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            isActive ? Icons.check_circle : Icons.radio_button_unchecked,
                            color: isActive ? const Color(0xFF00A86B) : const Color(0xFF9CA3AF),
                            size: 18,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              maskedKey,
                              style: TextStyle(
                                fontFamily: 'monospace',
                                fontSize: 13,
                                color: isActive ? const Color(0xFF065F46) : const Color(0xFF374151),
                                fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                              ),
                            ),
                          ),
                          if (!isActive)
                            IconButton(
                              icon: const Icon(Icons.check, color: Color(0xFF00A86B), size: 18),
                              onPressed: () => _selectGeminiKey(key),
                              padding: EdgeInsets.zero,
                              constraints: const BoxConstraints(),
                              tooltip: 'Use this key',
                            ),
                          const SizedBox(width: 10),
                          IconButton(
                            icon: const Icon(Icons.delete_outline, color: Colors.red, size: 18),
                            onPressed: () => _deleteGeminiKey(key),
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            tooltip: 'Delete key',
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 28),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _settingsSaving ? null : _saveSettings,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00A86B),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            child: _settingsSaving
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text('Save Settings', style: GoogleFonts.inter(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 15)),
          ),
        ),
        const SizedBox(height: 40),
      ],
    );
  }

  // ── HELPERS ──────────────────────────────────────────────────────

  Widget _urlPreset(String label, String url) {
    return GestureDetector(
      onTap: () => setState(() => _serverUrlCtrl.text = url),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F9FF),
          border: Border.all(color: const Color(0xFF2E86AB).withValues(alpha: 0.4)),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(label, style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF2E86AB), fontWeight: FontWeight.w500)),
      ),
    );
  }

  Future<void> _openModelPage(String modelName) async {
    final base = modelName.split(':')[0]; // strip tag e.g. qwen2.5:1.5b → qwen2.5
    final uri = Uri.parse('https://ollama.com/library/$base');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Widget _sectionLabel(String text) {
    return Text(
      text,
      style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w700, color: const Color(0xFF6B7280), letterSpacing: 1.2),
    );
  }

  BoxDecoration _cardDecor() {
    return BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 3))],
    );
  }

  Widget _chip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
      child: Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
    );
  }

  Widget _outlineBtn(String label, VoidCallback onTap) {
    return OutlinedButton(
      onPressed: onTap,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        side: const BorderSide(color: Color(0xFF00A86B)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        minimumSize: const Size(0, 32),
      ),
      child: Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: const Color(0xFF00A86B))),
    );
  }

  Widget _statRow(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, size: 18, color: const Color(0xFF9CA3AF)),
        const SizedBox(width: 10),
        Text(label, style: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF374151))),
        const Spacer(),
        Text(value, style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: const Color(0xFF00A86B))),
      ],
    );
  }

  Widget _sliderRow({
    required String label,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required String display,
    required String hint,
    required void Function(double) onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 14)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
              decoration: BoxDecoration(color: const Color(0xFF00A86B).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
              child: Text(display, style: GoogleFonts.inter(fontWeight: FontWeight.w700, fontSize: 14, color: const Color(0xFF00A86B))),
            ),
          ],
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          divisions: divisions,
          activeColor: const Color(0xFF00A86B),
          inactiveColor: const Color(0xFFE5E7EB),
          onChanged: onChanged,
        ),
        Text(hint, style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF9CA3AF))),
      ],
    );
  }

  Widget _dropdownRow({
    required String label,
    required String value,
    required Map<String, String> items,
    required void Function(String?) onChanged,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: GoogleFonts.inter(fontWeight: FontWeight.w600, color: const Color(0xFF1F2937), fontSize: 14)),
        DropdownButton<String>(
          value: items.containsKey(value) ? value : items.keys.first,
          underline: const SizedBox(),
          style: GoogleFonts.inter(fontSize: 13, color: const Color(0xFF374151)),
          items: items.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
          onChanged: onChanged,
        ),
      ],
    );
  }
}
