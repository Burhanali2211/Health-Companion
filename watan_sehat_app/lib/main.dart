import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'providers/chat_provider.dart';
import 'screens/chat_screen.dart';
import 'services/api_service.dart';
import 'services/model_manager_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiService.initBaseUrl();
  final modelManager = ModelManagerService();
  await modelManager.init();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: modelManager),
        ChangeNotifierProvider(create: (_) => ChatProvider()),
      ],
      child: HealthWellnessApp(),
    ),
  );
}

class HealthWellnessApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Health Wellness Companion',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        primaryColor: Color(0xFF3B82F6),
        scaffoldBackgroundColor: Color(0xFFF9FAFB),
        textTheme: GoogleFonts.interTextTheme(
          Theme.of(context).textTheme.apply(bodyColor: Color(0xFF1F2937), displayColor: Color(0xFF111827)),
        ),
      ),
      home: ChatScreen(),
    );
  }
}
