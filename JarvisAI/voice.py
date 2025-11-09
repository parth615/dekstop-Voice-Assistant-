import pyttsx3
import speech_recognition as sr
import config
from queue import Queue, Empty

engine = pyttsx3.init()
engine.setProperty('rate', config.VOICE_RATE)
try:
    engine.setProperty('voice', config.VOICE_ID)
except Exception:

    print("Warning: Specific voice ID not found. Using default voice.")


speech_queue = Queue()


log_to_ui_callback = None


def set_ui_log_callback(callback_function):
    """Sets the callback function from the UI to log messages."""
    global log_to_ui_callback
    log_to_ui_callback = callback_function


def say(text):
    """Converts text to speech and prints it (non-blocking)."""

    print(f"Assistant: {text}")

    if log_to_ui_callback:
        log_to_ui_callback(f"Assistant: {text}", "navy")


    speech_queue.put(text)


def listen():
    """Listens for audio input and returns the recognized text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        if log_to_ui_callback:
            log_to_ui_callback("<font color='darkorange'><b>Listening for Command...</b></font>", "darkorange")

        print("\n🎤 Listening...")
        recognizer.pause_threshold = 1
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("No speech detected.")
            return ""

    try:
        query = recognizer.recognize_google(audio, language='en-in')
        print(f"You said: {query}")
        if log_to_ui_callback:
            log_to_ui_callback(f"You said: {query}", "black")

        return query.lower()
    except sr.UnknownValueError:
        say("Sorry, I didn't catch that. Please repeat.")
        return ""
    except sr.RequestError:
        say("Speech service unavailable. Please check your internet connection.")
        return ""
    except Exception as e:
        print(f"Recognition error: {e}")
        return ""