import os
import subprocess
import webbrowser
import requests
import datetime
import time
import math
import wikipedia
import config
from voice import say
import shlex
import sys
import platform
import pyperclip
import json
try:
    import psutil
except ImportError:
    psutil = None

MEMORY_FILE = config.MEMORY_FILE
NOTES_FILE = config.NOTES_FILE

def load_memory():
    """Loads the memory dictionary from the JSON file."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Warning: Could not load or parse memory file.")
            return {}
    return {}


def save_memory(memory_data):
    """Saves the memory dictionary to the JSON file."""
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory_data, f, indent=4)
    except IOError:
        print("Error: Could not save memory file.")


def remember_fact(query):
    """Parses a query to extract a key-value fact and saves it."""
    memory = load_memory()


    if "is" in query:
        parts = query.split(" is ", 1)


        key_part = parts[0].replace("remember", "").replace("that", "").replace("my", "").strip()
        value_part = parts[1].strip()

        key = key_part.replace("your", "").replace("a", "").replace("an", "").strip()
        key = key.lower().replace(" ", "_")

        if not key or not value_part:
            say("I couldn't clearly identify the fact you want me to remember. Try phrases like 'remember my favorite color is blue'.")
            return

        memory[key] = value_part.capitalize()
        save_memory(memory)
        say(f"Okay, I'll remember that your {key_part} is {value_part}.")
        print(f"Memory saved: {key_part} -> {value_part}")
    else:
        say("To save a fact, use a sentence with 'is', like 'remember my hometown is New Delhi'.")


def recall_fact(query):
    """Parses a query to find a key and recalls the corresponding value."""
    memory = load_memory()

    # Logic to identify the key being asked about
    key_phrases = query.replace("what is", "").replace("where is", "").replace("tell me about", "").replace(
        "what is my", "").replace("what are my", "").strip()
    key = key_phrases.split("?")[-1].split("your")[-1].split("my")[-1].strip()
    key = key.lower().replace(" ", "_")

    if key in memory:
        say(f"I remember you told me that your {key.replace('_', ' ')} is {memory[key]}.")
    elif key:
        say(f"I don't specifically remember anything about your {key.replace('_', ' ')}. Would you like me to remember it?")
    else:
        say("What personal fact would you like me to recall?")


def forget_fact(query):
    """Parses a query to find a key and deletes the fact from memory."""
    memory = load_memory()

    key_phrases = query.replace("forget that", "").replace("forget about", "").replace(
        "delete the fact that", "").replace("clear my", "").strip()
    key = key_phrases.split("?")[-1].split("your")[-1].split("my")[-1].strip()
    key = key.lower().replace(" ", "_")

    if key in memory:
        value = memory.pop(key)
        save_memory(memory)
        say(f"I have successfully forgotten that your {key.replace('_', ' ')} was {value}.")
    elif key:
        say(f"I don't seem to have a fact stored for {key.replace('_', ' ')}.")
    else:
        say("Please specify the fact you want me to forget.")

def delete_file(query):
    """Safely deletes a file specified in the query (must be explicit)."""
    parts = query.split("delete file")[-1].split("remove file")[-1].strip()

    filename = parts.split("called")[-1].strip().strip('."\'')

    if not filename:
        say("I need the exact name of the file to delete. Please be careful with this command.")
        return

    file_path = os.path.expanduser(filename)

    if not os.path.exists(file_path):
        say(f"Error: The file '{filename}' was not found at the expected location.")
        return
    if not file_path.startswith(os.path.expanduser("~")):
        say("For security reasons, I can only delete files within your home directory.")
        return

    try:
        os.remove(file_path)
        say(f"Successfully deleted the file: {filename}")
        print(f"Deleted file: {file_path}")
    except PermissionError:
        say(f"Error: I do not have permission to delete the file: {filename}")
    except Exception as e:
        say(f"An unexpected error occurred while trying to delete the file: {filename}")
        print(f"File Deletion Error: {e}")

def create_note(query):
    """Creates a timestamped note/journal entry in a dedicated file."""
    note_content = query.replace("create note", "").replace("make a note", "").replace("write down", "").replace("journal that", "").strip()

    if not note_content:
        say("What would you like the note to say?")
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_note = f"\n--- {timestamp} ---\n{note_content}\n"

    try:
        with open(NOTES_FILE, "a") as f:
            f.write(formatted_note)
        say(f"Noted! I've saved a new entry: {note_content[:30]}...")
    except Exception:
        say("Sorry, I couldn't save your note.")


def set_system_volume(query):
    """Attempts to set the system volume to a specified percentage (macOS/Linux)."""
    parts = query.split()
    target_volume = None

    for i, part in enumerate(parts):
        try:
            val = int(part.strip('%'))
            if 0 <= val <= 100:
                target_volume = val
                break
        except ValueError:
            continue

    if target_volume is None:
        say("Please specify a volume level, like fifty percent, or set volume to eighty.")
        return

    try:
        if platform.system() == "Darwin": # macOS
            # Volume is 0-1.0 on macOS for 'osascript'
            subprocess.run(["osascript", "-e", f"set volume output volume {target_volume}"], check=True)
            say(f"Setting system volume to {target_volume} percent.")
        elif platform.system() == "Linux": # Linux (requires 'amixer' or similar)
            # This is a common method but may require a specific package (e.g., alsa-utils)
            subprocess.run(["amixer", "set", "Master", f"{target_volume}%"], check=True)
            say(f"Setting system volume to {target_volume} percent.")
        elif platform.system() == "Windows":
            # Windows requires specific libraries or PowerShell commands which are more complex.
            say("Direct volume control is complex on Windows and is not yet supported.")
        else:
            say("Volume control is not supported on this operating system.")

    except subprocess.CalledProcessError:
        say("I couldn't change the system volume. Make sure the necessary system tools are installed.")
    except Exception as e:
        say("An error occurred while trying to control the volume.")
        print("Volume Control Error:", e)


def run_diagnostics():
    """Checks and reports system usage metrics (CPU, Memory, Battery)."""
    if psutil is None:
        say("The psutil library is required for system diagnostics. Please install it with: pip install psutil")
        return

    try:
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1)

        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        total_mem_gb = memory.total / (1024 ** 3)
        available_mem_gb = memory.available / (1024 ** 3)

        battery_info = psutil.sensors_battery()
        battery_status = ""
        if battery_info:
            percent = battery_info.percent
            is_charging = "and is currently charging" if battery_info.power_plugged else "and is running on battery"
            battery_status = f"Your battery is at {percent} percent {is_charging}. "
        else:
            battery_status = "Battery status could not be retrieved. "

        say(f"Running system diagnostics. {battery_status}CPU usage is currently at {cpu_percent} percent. You are using {mem_percent} percent of your memory, with {available_mem_gb:.2f} gigabytes available out of {total_mem_gb:.2f} gigabytes total.")

    except Exception as e:
        say("An error occurred while trying to run system diagnostics.")
        print(f"Diagnostics Error: {e}")

def convert_units(query):
    """Handles simple unit conversions (e.g., temperature, distance)."""
    try:
        parts = query.lower().split()
        value = None
        for part in parts:
            try:
                value = float(part)
                break
            except ValueError:
                continue

        if value is None:
            say("I couldn't find a numerical value to convert.")
            return

        # Conversion rules
        if "celsius to fahrenheit" in query or "c to f" in query:
            result = (value * 9/5) + 32
            say(f"{value} degrees Celsius is {result:.2f} degrees Fahrenheit.")
        elif "fahrenheit to celsius" in query or "f to c" in query:
            result = (value - 32) * 5/9
            say(f"{value} degrees Fahrenheit is {result:.2f} degrees Celsius.")
        elif "miles to kilometers" in query or "mi to km" in query:
            result = value * 1.60934
            say(f"{value} miles is {result:.2f} kilometers.")
        elif "kilometers to miles" in query or "km to mi" in query:
            result = value / 1.60934
            say(f"{value} kilometers is {result:.2f} miles.")
        elif "kilograms to pounds" in query or "kg to lbs" in query:
            result = value * 2.20462
            say(f"{value} kilograms is {result:.2f} pounds.")
        else:
            say("I recognize the value, but please specify a supported conversion like 'Celsius to Fahrenheit' or 'Miles to Kilometers'.")

    except Exception as e:
        say("I encountered an error during the unit conversion.")
        print(f"Conversion Error: {e}")

def search_local_files(keyword):
    """
    Searches the local filesystem for files matching a keyword in the user's home directory.
    """
    base_path = os.path.expanduser("~")

    say(f"Searching for files containing '{keyword}' in your home directory. This may take a moment.")
    print(f"File Search: Starting in {base_path} for '{keyword}'")

    found_files = []
    search_limit = 5

    try:
        for root, dirs, files in os.walk(base_path, topdown=True):
            # Exclude common system/hidden directories for performance
            dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ('library', 'appdata', 'node_modules')]

            for file in files:
                if keyword.lower() in file.lower():
                    found_files.append(os.path.join(root, file))
                    if len(found_files) >= search_limit:
                        break
            if len(found_files) >= search_limit:
                break
    except Exception as e:
        say("An error occurred during file search due to permission issues.")
        print(f"File Search Error: {e}")
        return

    if found_files:
        say(f"I found {len(found_files)} files related to '{keyword}'. The first one is: {found_files[0]}. I have printed the full list to the console/log.")
        print("--- Found Files ---")
        for i, f in enumerate(found_files):
            print(f"({i+1}): {f}")
        print("-------------------")
    else:
        say(f"Sorry, I couldn't find any files matching '{keyword}' in your main directories.")

def process_clipboard():
    """Fetches the current clipboard content and automatically processes it."""
    try:
        content = pyperclip.paste()
        if not content:
            say("Your clipboard is currently empty.")
            return

        display_content = content[:50] + "..." if len(content) > 50 else content

        if len(content) < 150 and '\n' not in content:
            say(f"Your clipboard contains: {display_content}. Searching the web for this now.")
            search_web_general(content)
        else:
            say(f"Your clipboard contains a large block of text. I'm printing the full content to the application log/console.")
            print("\n--- Clipboard Content ---")
            print(content)
            print("-------------------------\n")

    except Exception as e:
        say("I couldn't access your clipboard. Please make sure the 'pyperclip' library is installed.")
        print(f"Clipboard Error: {e}")

def plan_trip_search(query):
    """
    Guides the user to major travel search engines (Google Flights/Hotels)
    based on the query, focusing on budget awareness.
    """
    say("I cannot book or handle payments directly, but I can open a smart search for you on major travel websites.")

    destination = ""
    budget = ""
    date = ""

    if "to" in query:
        parts = query.split("to", 1)
        if len(parts) > 1:
            destination_candidate = parts[-1].split("for")[0].split("on")[0].split("next")[0].strip()
            if destination_candidate:
                destination = destination_candidate

    if "budget of" in query:
        budget = query.split("budget of")[-1].split("on")[0].strip()
    elif "under" in query:
        budget_parts = query.split("under")
        if len(budget_parts) > 1:
            budget = budget_parts[-1].split("on")[0].strip()

    if "on" in query:
        date_parts = query.split("on")
        if len(date_parts) > 1:
            date = date_parts[-1].strip()

    search_term = f"flights and hotels to {destination}" if destination else "trip planner"
    base_url = "https://www.google.com/search?q="
    search_parts = [search_term]

    if date:
        search_parts.append(f"on {date}")
    if budget:
        search_parts.append(f"budget under {budget}")

    final_query = "+".join(search_parts).replace(" ", "+")
    search_url = base_url + final_query

    webbrowser.open(search_url)

    if destination:
        budget_info = f" with a budget target of {budget}" if budget else ""
        say(f"I've opened Google Search for trips to {destination}{budget_info} to help you plan your journey.")
    else:
        say("I've opened a Google Search for trip planning to help you get started.")

# ---------- STANDARD UTILITIES (Included for completeness) ----------

def get_time():
    """Tells the current time."""
    now = datetime.datetime.now()
    current_time = now.strftime("%I:%M %p")
    say(f"The current time is {current_time}.")

def get_date():
    """Tells the current date."""
    today = datetime.datetime.now()
    current_date = today.strftime("%A, %B %d, %Y")
    say(f"Today's date is {current_date}.")

def perform_calculation(expression):
    """Evaluates a mathematical expression."""
    try:
        expression = expression.replace("times", "*").replace("multiplied by", "*")
        expression = expression.replace("divided by", "/").replace("over", "/")
        expression = expression.replace("plus", "+").replace("minus", "-")
        expression = expression.replace("^", "**").replace("power of", "**")
        result = eval(expression, {"__builtins__": None}, math.__dict__)
        say(f"The answer is {result}")
    except Exception:
        say("Sorry, I couldn't calculate that.")

def open_app(app_name):
    """Opens a specified application (Cross-platform compatible attempt)."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", "-a", app_name], check=True)
        elif platform.system() == "Windows":
            subprocess.run(["start", app_name], check=True, shell=True)
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", app_name], check=True)
        say(f"Opening {app_name}")
    except subprocess.CalledProcessError:
        say(f"Couldn't find or open the app {app_name}.")
    except Exception as e:
        say(f"An error occurred trying to open {app_name}")
        print("Open App Error:", e)

def open_website(url):
    """Opens a website in the default browser."""
    if not url.startswith("http"):
        url = f"https://{url}"
    webbrowser.open(url)
    say(f"Opening {url}")

def search_web_general(query):
    """Performs a web search for any non-specific query."""
    say(f"I don't have a direct answer for that. Searching the web for: {query}")
    search_url = f"https://www.google.com/search?q={query}"
    webbrowser.open(search_url)

def shutdown():
    """Initiates system shutdown (platform specific)."""
    say("Shutting down your computer in 10 seconds. You have a chance to cancel.")
    if platform.system() == "Darwin":
        os.system("sudo shutdown -h +10")
    elif platform.system() == "Windows":
        os.system("shutdown /s /t 10")
    elif platform.system() == "Linux":
        os.system("sudo shutdown -h 10")
    else:
        say("Shutdown command not supported on this OS.")

def restart():
    """Initiates system restart (platform specific)."""
    say("Restarting your computer in 10 seconds.")
    if platform.system() == "Darwin":
        os.system("sudo shutdown -r +10")
    elif platform.system() == "Windows":
        os.system("shutdown /r /t 10")
    elif platform.system() == "Linux":
        os.system("sudo shutdown -r 10")
    else:
        say("Restart command not supported on this OS.")

def search_maps(query):
    """Opens Google Maps for a given query (location/directions)."""
    try:
        search_term = query.replace("directions to", "").replace("map of", "").replace("show me", "").strip()
        if not search_term:
            say("Which location or directions should I search for on the map?")
            return
        say(f"Searching Google Maps for {search_term}")
        maps_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
        webbrowser.open(maps_url)
    except Exception as e:
        say("Sorry, I couldn't open the maps service.")

def search_youtube(query):
    """Searches YouTube and opens the result."""
    try:
        search_term = query.replace("search youtube for", "").replace("find on youtube", "").strip()
        if not search_term:
            say("What video should I search for on YouTube?")
            return
        say(f"Searching YouTube for {search_term}")
        youtube_url = f"https://www.youtube.com/results?search_query={search_term.replace(' ', '+')}"
        webbrowser.open(youtube_url)
    except Exception as e:
        say("Sorry, I couldn't open YouTube.")

def play_music():
    """Opens the default music app or falls back to YouTube Music web."""
    app_name = "Spotify" if platform.system() in ["Darwin", "Windows"] else "Rhythmbox"
    try:
        open_app(app_name)
        say(f"Attempting to open {app_name}.")
    except Exception:
        say("Couldn't open the music application. Opening YouTube Music in the browser.")
        webbrowser.open("https://music.youtube.com")

def get_weather(city="Delhi"):
    """Fetches and reports the current weather for a specified city."""
    if not config.WEATHER_API_KEY:
        say("Weather API key is missing. Please set it in config.py.")
        return
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={config.WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=5).json()
        if res.get("cod") == 200:
            temp = res["main"]["temp"]
            desc = res["weather"][0]["description"]
            humidity = res["main"]["humidity"]
            wind_speed = res["wind"]["speed"]
            say(f"The temperature in {city} is {temp}°C with {desc}. Humidity is {humidity} percent and wind speed is {wind_speed} meters per second.")
        elif res.get("cod") == "404":
            say(f"City '{city}' not found.")
        else:
            say("Could not fetch weather data due to an API issue.")
    except Exception as e:
        say("Couldn't fetch the weather.")

def get_news():
    """Fetches and reports the top news headlines."""
    if not config.NEWS_API_KEY:
        say("News API key is missing. Please set it in config.py.")
        return
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={config.NEWS_API_KEY}"
        res = requests.get(url, timeout=5).json()
        articles = res.get("articles", [])[:5]
        if not articles:
            say("I couldn't find any latest news.")
            return
        say(f"Here are the top {len(articles)} headlines for today.")
        for i, article in enumerate(articles, start=1):
            title = article.get("title", "No title")
            say(f"Headline {i}: {title}")
        say("That's all the latest news for now.")
    except Exception as e:
        say("Sorry, I couldn't fetch the latest news.")

def search_wikipedia(query):
    """Searches Wikipedia and provides a summary."""
    try:
        summary = wikipedia.summary(query, sentences=3, auto_suggest=True, redirect=True)
        full_response = "According to Wikipedia, "
        sentences = [s.strip() for s in summary.split('.') if s.strip()]
        full_response += ". ".join(sentences) + "."
        say(full_response)
    except wikipedia.exceptions.PageError:
        say(f"Sorry, I couldn't find a Wikipedia page for {query}.")
    except wikipedia.exceptions.DisambiguationError as e:
        options = ", ".join(e.options[:3])
        say(f"Your search for {query} is ambiguous. Did you mean: {options}?")
    except Exception as e:
        say("An error occurred while searching Wikipedia.")

def tell_a_joke():
    """Fetches a random joke from a public API."""
    try:
        url = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit"
        res = requests.get(url, timeout=5).json()
        if res.get('type') == 'single':
            joke = res.get('joke')
            say(joke)
        elif res.get('type') == 'twopart':
            setup = res.get('setup')
            delivery = res.get('delivery')
            say(setup)
            time.sleep(1)
            say(delivery)
        else:
             say("I'm having trouble connecting to my humor database, but here's one: Why did the programmer quit his job? Because he didn't get arrays!")
    except Exception as e:
        say("Sorry, I can't think of a joke right now.")

def add_todo(task):
    """Adds a task to the to-do list file."""
    try:
        with open(config.TODO_FILE, "a") as f:
            f.write(f"- {task.strip()}\n")
        say(f"Added '{task.strip()}' to your to-do list.")
    except Exception:
        say("Sorry, I couldn't save the task.")

def view_todo():
    """Reads and speaks the current to-do list."""
    try:
        if not os.path.exists(config.TODO_FILE) or os.stat(config.TODO_FILE).st_size == 0:
            say("Your to-do list is empty. Do you want to add a task?")
            return
        with open(config.TODO_FILE, "r") as f:
            tasks = f.readlines()
        if not tasks:
            say("Your to-do list is empty.")
            return
        say("Here are your current tasks:")
        for i, task in enumerate(tasks):
            say(f"Task {i + 1}: {task.strip().lstrip('- ')}")
    except Exception:
        say("Sorry, I couldn't read your to-do list.")

def clear_todo():
    """Clears the to-do list file."""
    try:
        if os.path.exists(config.TODO_FILE):
            os.remove(config.TODO_FILE)
            say("Your to-do list has been cleared.")
        else:
            say("Your to-do list is already empty.")
    except Exception:
        say("Sorry, I couldn't clear your to-do list.")