import os
NEWS_API_KEY = "0b852da4ff4a4ec69864694e28959f4a"
WEATHER_API_KEY = "5924ecfd1608208d971180cc17bef084"

base_dir = os.path.join(os.path.expanduser("~"), "Documents", "Jarvis_Data")
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

TODO_FILE = os.path.join(base_dir, "todo_list.txt")
MEMORY_FILE = os.path.join(base_dir, "assistant_memory.json")
NOTES_FILE = os.path.join(base_dir, "assistant_notes.txt")
LANGUAGE_CODE = 'en-US'
VOICE_RATE = 170
VOICE_ID = 'com.apple.speech.synthesis.voice.samantha'