import datetime
import os
import config
from voice import say, listen
import commands
import shlex


def main():
    """The main loop for the voice assistant."""
    say("Hello Parth! Your modular voice assistant is ready.")

    while True:
        query = listen()

        if not query:
            continue

        if "exit" in query or "bye" in query or "stop listening" in query:
            say("Goodbye Parth, take care!")
            break

        elif query.startswith(("open ", "launch ")):
            content = query.replace("open ", "", 1).replace("launch ", "", 1).strip()

            if any(term in query for term in ["website", "site", "go to", "url"]) or any(
                    suffix in content for suffix in [".com", ".org", ".net", ".edu", ".gov"]):

                if "go to" in query:
                    site = query.split("go to")[-1].strip()
                elif "open website" in query:
                    site = query.split("open website")[-1].strip()
                else:
                    site = content

                commands.open_website(site)

            else:
                app = content

                if app.lower() == "chrome":
                    commands.open_app("Google Chrome")
                elif app.lower() in ["app", "application"]:
                    say("Please specify the application name after saying 'open'.")
                else:
                    commands.open_app(app)


        elif "shutdown" in query:
            commands.shutdown()
        elif "restart" in query:
            commands.restart()
        elif any(phrase in query for phrase in
                 ["run diagnostics", "check system", "check memory", "check battery", "system status"]):
            commands.run_diagnostics()
        elif "convert" in query or "conversion" in query:
            commands.convert_units(query)
        elif any(phrase in query for phrase in
                 ["what's copied", "read clipboard", "process clipboard", "what did i copy"]):
            commands.process_clipboard()
        elif query.startswith(("search file for", "find file for", "search local for")):
            keyword = query.split("for")[-1].strip()
            if keyword:
                commands.search_local_files(keyword)
            else:
                say("Please provide a keyword to search for.")
        elif any(phrase in query for phrase in ["plan a trip", "book a flight", "find a hotel", "trip to", "commute"]):
            commands.plan_trip_search(query)
        elif any(phrase in query for phrase in ["directions to", "map of", "show me on map", "where is"]):
            commands.search_maps(query)
        elif any(phrase in query for phrase in ["search youtube", "find on youtube", "play on youtube"]):
            commands.search_youtube(query)
        elif any(phrase in query for phrase in
                 ["remember that", "save this fact", "my name is", "i am called", "i live in"]):
            commands.remember_fact(query)
        elif any(phrase in query for phrase in
                 ["what is my", "what is your favorite", "where is my", "tell me about my"]):
            commands.recall_fact(query)
        elif "weather" in query:
            city = query.split("in")[-1].strip() if "in" in query else "Delhi"
            commands.get_weather(city)
        elif "news" in query:
            commands.get_news()
        elif "time" in query:
            commands.get_time()
        elif "date" in query or "today's date" in query:
            commands.get_date()
        elif "wikipedia" in query or "tell me about" in query:
            term = query.split("wikipedia")[-1].split("tell me about")[-1].strip()
            if term:
                commands.search_wikipedia(term)
            else:
                say("What would you like me to search on Wikipedia?")
        elif "tell me a joke" in query or "joke" in query:
            commands.tell_a_joke()
        elif "add to do" in query or "add task" in query:
            task = query.split("add to do")[-1].split("add task")[-1].strip()
            if task:
                commands.add_todo(task)
            else:
                say("What task would you like to add?")
        elif "view to do" in query or "what are my tasks" in query:
            commands.view_todo()
        elif "clear to do" in query:
            commands.clear_todo()
        elif "music" in query or "spotify" in query or "play" in query:
            commands.play_music()
        elif any(word in query for word in
                 ["plus", "minus", "times", "divide", "+", "-", "*", "/", "^", "square", "root", "sin", "cos", "tan",
                  "calculate"]):
            expr = query.replace("what is", "").replace("calculate", "").replace("?", "").strip()
            commands.perform_calculation(expr)

        else:
            commands.search_web_general(query)


if __name__ == "__main__":
    main()