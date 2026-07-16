import 'package:flutter/material.dart';
import '../services/api_service.dart';

import '../services/model_manager_service.dart';
import 'package:llama_cpp_dart/llama_cpp_dart.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({required this.text, required this.isUser})
      : timestamp = DateTime.now();
}

class ChatProvider with ChangeNotifier {
  final ApiService _apiService = ApiService();
  final ModelManagerService _modelManager = ModelManagerService();
  
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  List<ChatMessage> get messages => _messages;
  bool get isLoading => _isLoading;

  List<Map<String, String>> getChatHistory() {
    final recent = _messages.length > 10
        ? _messages.sublist(_messages.length - 10)
        : List<ChatMessage>.from(_messages);
    return recent
        .map((m) => {'role': m.isUser ? 'user' : 'assistant', 'content': m.text})
        .toList();
  }

  void addMessage(String text, bool isUser) {
    _messages.add(ChatMessage(text: text, isUser: isUser));
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    addMessage(text, true);
    _isLoading = true;
    notifyListeners();

    String response = "";
    
    final prefs = await SharedPreferences.getInstance();
    final useOnlineGemini = prefs.getBool('use_online_gemini') ?? false;
    final geminiApiKey = prefs.getString('active_gemini_api_key') ?? '';

    // Check if an on-device model is loaded and ready
    if (_modelManager.llama != null && !_modelManager.isLlamaLoading) {
        response = await _modelManager.generateResponse(text);
    } else if (useOnlineGemini && geminiApiKey.isNotEmpty) {
        final history = getChatHistory();
        response = await _apiService.askGeminiDirectly(text, geminiApiKey, history);
    } else {
        // Fallback to local server/cloud API
        final history = getChatHistory();
        response = await _apiService.askCompanion(text, 'Srinagar', 'Winter', 30, history);
    }

    _isLoading = false;
    addMessage(response, false);
  }

  void clearChat() {
    _messages.clear();
    notifyListeners();
  }
}
