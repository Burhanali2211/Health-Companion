import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/model_manager_service.dart';

class ModelDownloadScreen extends StatefulWidget {
  @override
  _ModelDownloadScreenState createState() => _ModelDownloadScreenState();
}

class _ModelDownloadScreenState extends State<ModelDownloadScreen> {
  @override
  void initState() {
    super.initState();
    _checkDownloadedModels();
  }

  Future<void> _checkDownloadedModels() async {
    // Just trigger a rebuild after init if needed
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final modelManager = Provider.of<ModelManagerService>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline AI Models'),
        elevation: 0,
        backgroundColor: Theme.of(context).primaryColor,
        foregroundColor: Colors.white,
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: modelManager.availableModels.length,
        itemBuilder: (context, index) {
          final model = modelManager.availableModels[index];
          final isDownloading = modelManager.isDownloading[model.id] ?? false;
          final progress = modelManager.downloadProgress[model.id] ?? 0.0;
          final isActive = modelManager.activeModelId == model.id;

          return Card(
            margin: const EdgeInsets.only(bottom: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          model.name,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      if (isActive)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          decoration: BoxDecoration(
                            color: Colors.green.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Text(
                            'ACTIVE',
                            style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    model.description,
                    style: TextStyle(color: Colors.grey[700]),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Size: ${model.sizeInMB} MB',
                    style: TextStyle(color: Colors.grey[600], fontSize: 12),
                  ),
                  const SizedBox(height: 16),
                  
                  // FutureBuilder to check if downloaded
                  FutureBuilder<bool>(
                    future: modelManager.isModelDownloaded(model.id),
                    builder: (context, snapshot) {
                      final isDownloaded = snapshot.data ?? false;

                      if (isDownloading) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            LinearProgressIndicator(value: progress),
                            const SizedBox(height: 8),
                            Text('${(progress * 100).toStringAsFixed(1)}% downloaded', textAlign: TextAlign.center),
                          ],
                        );
                      }

                      if (isDownloaded) {
                        return Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton.icon(
                              icon: const Icon(Icons.delete, color: Colors.red),
                              label: const Text('Delete', style: TextStyle(color: Colors.red)),
                              onPressed: () {
                                // Add delete logic later if needed
                              },
                            ),
                            const SizedBox(width: 8),
                            ElevatedButton(
                              onPressed: isActive 
                                  ? null 
                                  : () => modelManager.setActiveModel(model.id),
                              child: Text(isActive ? 'Currently Using' : 'Select Model'),
                            ),
                          ],
                        );
                      }

                      return SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.download),
                          label: const Text('Download Offline Model'),
                          onPressed: () => modelManager.downloadModel(model.id),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
