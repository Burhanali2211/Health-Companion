import { useState, useRef, useCallback } from "react"
import axios from "axios"

export function useVoice(ageMode = "jawaan", pageContext = "") {
  const [state, setState] = useState("idle")
  const [transcript, setTranscript] = useState("")
  const [response,   setResponse]   = useState(null)
  
  const recognitionRef = useRef(null)
  const transcriptRef = useRef("")

  const startListening = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setState("error");
      setTranscript("Speech recognition not supported in this browser.");
      setTimeout(() => setState("idle"), 3000);
      return;
    }

    try {
      // Create recognition object on the fly inside the click handler for iOS Safari compatibility
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US'; 
      
      recognition.onstart = () => {
        setState("listening")
        setTranscript("")
        transcriptRef.current = ""
        setResponse(null)
      }
      
      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        const newTranscript = finalTranscript || interimTranscript;
        setTranscript(newTranscript);
        transcriptRef.current = newTranscript;
      }
      
      recognition.onend = async () => {
        const finalWord = transcriptRef.current.trim()
        if (finalWord.length === 0) {
          setState("idle")
          return;
        }
        
        setState("processing")
        
        try {
          const askRes = await axios.post("/api/companion/ask", {
            query: finalWord, age_mode: ageMode, district: "srinagar", language: "auto", page_context: pageContext
          })
          setResponse(askRes.data.data)
          setState("speaking")

          const ttsRes = await axios.post(
            "/api/voice/tts",
            { text: askRes.data.data?.response_text ?? "", age_mode: ageMode, language: "auto" },
            { responseType: "blob" }
          )
          
          if (ttsRes.data?.size > 0) {
            const audio = new Audio(URL.createObjectURL(ttsRes.data))
            audio.onended = () => setState("idle")
            audio.play()
          } else {
            setTimeout(() => setState("idle"), 3000)
          }
        } catch (err) {
          console.error(err)
          setState("error")
          setTimeout(() => setState("idle"), 3000)
        }
      }
      
      recognition.onerror = (event) => {
        if (event.error !== 'no-speech') {
          setState("error");
          setTimeout(() => setState("idle"), 3000);
        } else {
          setState("idle");
        }
      }
      
      recognitionRef.current = recognition;
      recognition.start();
    } catch (e) {
      console.log("Already started or blocked by browser:", e);
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }, [ageMode, pageContext]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  }, []);

  return { state, transcript, response, startListening, stopListening }
}
