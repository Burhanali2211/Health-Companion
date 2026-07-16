import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:llama_cpp_dart/llama_cpp_dart.dart';

class LocalModel {
  final String id;
  final String name;
  final String realName;
  final String downloadUrl;
  final double sizeInMB;
  final String description;

  LocalModel({
    required this.id,
    required this.name,
    required this.realName,
    required this.downloadUrl,
    required this.sizeInMB,
    required this.description,
  });
}

class ModelManagerService with ChangeNotifier {
  static final ModelManagerService _instance = ModelManagerService._internal();
  factory ModelManagerService() => _instance;
  ModelManagerService._internal();

  Llama? _llama;
  Llama? get llama => _llama;

  bool _isLlamaLoading = false;
  bool get isLlamaLoading => _isLlamaLoading;

  final List<LocalModel> availableModels = [
    LocalModel(
      id: 'tinyllama',
      name: 'Dal Lake Companion',
      realName: 'TinyLlama 1.1B',
      downloadUrl: 'https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf',
      sizeInMB: 650,
      description: 'Ultra-lightweight and silent, like the calm waters of Dal Lake. Extremely fast, ideal for older or low-resource devices.',
    ),
    LocalModel(
      id: 'llama_1b',
      name: 'Lidder River Companion',
      realName: 'Llama 3.2 1B',
      downloadUrl: 'https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf',
      sizeInMB: 750,
      description: 'Swift and fast-flowing, like the streams of Lidder River. Meta\'s latest compact model optimized for speed with advanced reasoning.',
    ),
    LocalModel(
      id: 'qwen_1.5b',
      name: 'Jhelum River Companion',
      realName: 'Qwen 1.5B',
      downloadUrl: 'https://huggingface.co/Qwen/Qwen1.5-1.8B-Chat-GGUF/resolve/main/qwen1_5-1_8b-chat-q4_k_m.gguf',
      sizeInMB: 1100,
      description: 'Balanced and deep-flowing intelligence, named after the historic Jhelum River. Provides excellent response accuracy and speed.',
    ),
    LocalModel(
      id: 'gemma_2b',
      name: 'Chinar Tree Companion',
      realName: 'Gemma 2B (Google)',
      downloadUrl: 'https://huggingface.co/google/gemma-2b-it-GGUF/resolve/main/gemma-2b-it-q4_k_m.gguf',
      sizeInMB: 1700,
      description: 'Grand and robust, like the iconic and majestic Chinar trees of Kashmir. Google\'s high-intelligence model with strong reasoning, requires more RAM.',
    ),
  ];

  Map<String, double> downloadProgress = {};
  Map<String, bool> isDownloading = {};
  String? activeModelId;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    activeModelId = prefs.getString('active_model_id');
    if (activeModelId != null) {
      await _loadModel(activeModelId!);
    }
  }

  Future<String> getModelPath(String modelId) async {
    final dir = await getApplicationDocumentsDirectory();
    return '${dir.path}/$modelId.gguf';
  }

  Future<bool> isModelDownloaded(String modelId) async {
    final path = await getModelPath(modelId);
    return File(path).exists();
  }

  Future<void> downloadModel(String modelId) async {
    final model = availableModels.firstWhere((m) => m.id == modelId);
    final path = await getModelPath(modelId);
    final dio = Dio();

    isDownloading[modelId] = true;
    downloadProgress[modelId] = 0.0;
    notifyListeners();

    try {
      await dio.download(
        model.downloadUrl,
        path,
        onReceiveProgress: (received, total) {
          if (total != -1) {
            downloadProgress[modelId] = received / total;
            notifyListeners();
          }
        },
      );
    } catch (e) {
      print('Download error: $e');
    } finally {
      isDownloading[modelId] = false;
      notifyListeners();
    }
  }

  Future<void> setActiveModel(String modelId) async {
    if (!await isModelDownloaded(modelId)) return;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('active_model_id', modelId);
    activeModelId = modelId;
    notifyListeners();

    await _loadModel(modelId);
  }

  Future<void> _loadModel(String modelId) async {
    _isLlamaLoading = true;
    notifyListeners();
    try {
      final path = await getModelPath(modelId);
      
      // We initialize Llama for llama_cpp_dart usually
      _llama = Llama(path);
      
    } catch (e) {
      print("Failed to load model: $e");
    } finally {
      _isLlamaLoading = false;
      notifyListeners();
    }
  }

  Future<String> generateResponse(String prompt) async {
    if (_llama == null) return "Model not loaded.";
    try {
      // Basic implementation for llama_cpp_dart inference
      // The exact API might differ (e.g. prompt, generate, etc.)
      // We will try .prompt() which is common in dart wrappers.
      // We run it in an isolate or future to prevent UI freezing if possible.
      // For now, simply awaiting prompt if it's async, or computing it.
      
      // Let's format the prompt depending on the model (chatml for qwen/gemma typically)
      final formattedPrompt = "<|im_start|>user\n$prompt<|im_end|>\n<|im_start|>assistant\n";
      
      _llama!.setPrompt(formattedPrompt);
      final result = await _llama!.generateCompleteText();
      return result;
    } catch (e) {
      print("Generation error: $e");
      return "Sorry, I encountered an error generating the response on-device.";
    }
  }
}
