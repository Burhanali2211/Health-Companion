import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:typed_data';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String _defaultUrl = 'http://10.0.2.2:8000';
  static String _baseUrl = _defaultUrl;

  static String get baseUrl => _baseUrl;

  /// Call once at app start to load persisted server URL.
  static Future<void> initBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString('watan_server_url') ?? _defaultUrl;
  }

  static Future<void> setServerUrl(String url) async {
    final trimmed = url.trim().replaceAll(RegExp(r'/$'), '');
    _baseUrl = trimmed.isEmpty ? _defaultUrl : trimmed;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('watan_server_url', _baseUrl);
  }

  // Cached settings to avoid hitting /api/settings on every message
  Map<String, dynamic> _settings = {
    'district': 'srinagar',
    'age_mode': 'jawaan',
    'language': 'auto',
    'temperature': 0.7,
    'max_tokens': 200,
    'voice_speed': 1.0,
  };
  bool _settingsLoaded = false;

  Future<void> _ensureSettings() async {
    if (_settingsLoaded) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      final cached = prefs.getString('watan_settings');
      if (cached != null) {
        final decoded = jsonDecode(cached) as Map<String, dynamic>;
        _settings.addAll(decoded);
      }
      // Also try to sync from backend
      final res = await http.get(Uri.parse('$baseUrl/api/settings'))
          .timeout(const Duration(seconds: 2));
      if (res.statusCode == 200) {
        final data = (jsonDecode(res.body)['data'] as Map<String, dynamic>?) ?? {};
        _settings.addAll(data);
        await prefs.setString('watan_settings', jsonEncode(_settings));
      }
    } catch (_) {}
    _settingsLoaded = true;
  }

  void invalidateSettings() => _settingsLoaded = false;

  Future<String> askCompanion(
    String message,
    String district,
    String season,
    int age,
    List<Map<String, String>> chatHistory,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/companion/ask'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'query': message,
          'district': district.toLowerCase(),
          'age_mode': 'jawaan',
          'language': 'auto',
          'chat_history': chatHistory,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return (data['data']['response_text'] as String?) ?? 'No response.';
      } else {
        throw Exception('Server error ${response.statusCode}');
      }
    } catch (e) {
      return 'Could not connect to companion. Please check if the backend is running. ($e)';
    }
  }

  /// Streams SSE tokens. Calls [onToken] for each chunk, [onDone] when complete.
  Future<void> streamCompanionResponse({
    required String message,
    required List<Map<String, String>> chatHistory,
    required void Function(String token) onToken,
    required void Function() onDone,
    required void Function(String error) onError,
  }) async {
    await _ensureSettings();
    final client = http.Client();
    bool doneFired = false;
    void fireDone() {
      if (!doneFired) {
        doneFired = true;
        onDone();
      }
    }

    try {
      final request = http.Request('POST', Uri.parse('$baseUrl/api/companion/stream'));
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode({
        'query': message,
        'district': _settings['district'] ?? 'srinagar',
        'age_mode': _settings['age_mode'] ?? 'jawaan',
        'language': _settings['language'] ?? 'auto',
        'temperature': _settings['temperature'] ?? 0.7,
        'max_tokens': _settings['max_tokens'] ?? 200,
        'chat_history': chatHistory,
      });

      final streamedResponse = await client.send(request);

      await streamedResponse.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .forEach((line) {
        if (!line.startsWith('data: ')) return;
        final data = line.substring(6).trim();
        if (data == '[DONE]') {
          fireDone();
          return;
        }
        try {
          final json = jsonDecode(data) as Map<String, dynamic>;
          final token = json['text'] as String? ?? '';
          if (token.isNotEmpty) onToken(token);
        } catch (_) {}
      });

      fireDone();
    } catch (e) {
      onError(e.toString());
    } finally {
      client.close();
    }
  }

  Future<Map<String, dynamic>> getModels() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/models'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {}
    return {'status': 'error', 'data': {'models': [], 'active_model': ''}};
  }

  Future<bool> pullModel(String modelName) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/models/pull'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'model': modelName}),
      ).timeout(const Duration(minutes: 5));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> setActiveModel(String modelName) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/models/set-active'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'model': modelName}),
      ).timeout(const Duration(seconds: 8));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> deleteModel(String modelName) async {
    try {
      final res = await http.delete(Uri.parse('$baseUrl/api/models/${Uri.encodeComponent(modelName)}'))
          .timeout(const Duration(seconds: 8));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getRagStatus() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/rag/status'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {}
    return {'status': 'error', 'data': {}};
  }

  Future<bool> setRagEnabled(bool enabled) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/rag/toggle'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'enabled': enabled}),
      ).timeout(const Duration(seconds: 8));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> rebuildRag() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/rag/rebuild'))
          .timeout(const Duration(minutes: 3));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getSettings() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/settings'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {}
    return {'status': 'error', 'data': {}};
  }

  Future<bool> updateSettings(Map<String, dynamic> settings) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/settings'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(settings),
      ).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        _settings.addAll(settings);
        invalidateSettings();
        _settingsLoaded = true; // already have fresh data
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('watan_settings', jsonEncode(_settings));
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getStats() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/stats'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {}
    return {'status': 'error', 'data': {}};
  }

  Future<Uint8List?> synthesizeSpeech(String text, String language) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/voice/tts'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text, 'language': language}),
      );

      if (response.statusCode == 200) return response.bodyBytes;
    } catch (e) {
      // ignore TTS errors — voice mode continues
    }
    return null;
  }

  Future<String?> transcribeVoice(String filePath) async {
    try {
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/voice/stt'));
      request.files.add(await http.MultipartFile.fromPath('file', filePath));
      final response = await request.send();
      if (response.statusCode == 200) {
        final body = await response.stream.bytesToString();
        final data = jsonDecode(body);
        if (data['status'] == 'ok' && data['data'] != null) {
          return data['data']['transcript'] as String?;
        }
      }
    } catch (e) {
      // Ignore errors for now, return null
    }
    return null;
  }

  Future<String> askGeminiDirectly(
    String message,
    String apiKey,
    List<Map<String, String>> chatHistory,
  ) async {
    try {
      final systemPrompt = """You are Sehat Saathi, a warm and knowledgeable health companion built for Kashmir.
Answer the user's actual question directly — do not change the topic.
CRITICAL: Respond ONLY in the same language as the user's question. HARD LIMIT: 60 words maximum — stop immediately at 60 words. Never diagnose. Do not restate the question.""";

      final contents = chatHistory.map((m) {
        return {
          'role': m['role'] == 'assistant' ? 'model' : 'user',
          'parts': [{'text': m['content']}]
        };
      }).toList();

      final url = Uri.parse('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=\$apiKey');
      
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'systemInstruction': {
            'parts': [{'text': systemPrompt}]
          },
          'contents': contents,
          'generationConfig': {
            'temperature': 0.5,
            'maxOutputTokens': 200,
          }
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final candidates = data['candidates'] as List?;
        if (candidates != null && candidates.isNotEmpty) {
          final content = candidates[0]['content'];
          if (content != null) {
            final parts = content['parts'] as List?;
            if (parts != null && parts.isNotEmpty) {
              return (parts[0]['text'] as String?) ?? 'No response text.';
            }
          }
        }
        return 'Invalid response format from Gemini API.';
      } else {
        return 'Gemini API Error: ${response.statusCode} - ${response.body}';
      }
    } catch (e) {
      return 'Failed to connect to Gemini API. Check your internet connection. ($e)';
    }
  }

  Future<void> streamGeminiDirectly({
    required String message,
    required String apiKey,
    required List<Map<String, String>> chatHistory,
    required void Function(String token) onToken,
    required void Function() onDone,
    required void Function(String error) onError,
  }) async {
    final client = http.Client();
    bool doneFired = false;
    void fireDone() {
      if (!doneFired) {
        doneFired = true;
        onDone();
      }
    }

    try {
      final systemPrompt = """You are Sehat Saathi, a warm and knowledgeable health companion built for Kashmir.
Answer the user's actual question directly — do not change the topic.
CRITICAL: Respond ONLY in the same language as the user's question. HARD LIMIT: 60 words maximum — stop immediately at 60 words. Never diagnose. Do not restate the question.""";

      final contents = chatHistory.map((m) {
        return {
          'role': m['role'] == 'assistant' ? 'model' : 'user',
          'parts': [{'text': m['content']}]
        };
      }).toList();

      final url = Uri.parse('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?key=$apiKey');
      final request = http.Request('POST', url);
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode({
        'systemInstruction': {
          'parts': [{'text': systemPrompt}]
        },
        'contents': contents,
        'generationConfig': {
          'temperature': 0.5,
          'maxOutputTokens': 200,
        }
      });

      final streamedResponse = await client.send(request);
      StringBuffer buffer = StringBuffer();
      
      await streamedResponse.stream
          .transform(utf8.decoder)
          .forEach((chunk) {
            buffer.write(chunk);
            String content = buffer.toString();
            
            final regExp = RegExp(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"');
            final matches = regExp.allMatches(content);
            
            int lastMatchEnd = 0;
            for (final match in matches) {
              final val = match.group(1);
              if (val != null) {
                String decoded = val
                    .replaceAll(r'\n', '\n')
                    .replaceAll(r'\"', '"')
                    .replaceAll(r'\t', '\t')
                    .replaceAll(r'\\', '\\');
                
                decoded = decoded.replaceAllMapped(RegExp(r'\\u([0-9a-fA-F]{4})'), (m) {
                  return String.fromCharCode(int.parse(m.group(1)!, radix: 16));
                });
                
                onToken(decoded);
              }
              lastMatchEnd = match.end;
            }
            
            if (lastMatchEnd > 0) {
              final remaining = content.substring(lastMatchEnd);
              buffer.clear();
              buffer.write(remaining);
            }
          });

      fireDone();
    } catch (e) {
      onError(e.toString());
    } finally {
      client.close();
    }
  }
}
