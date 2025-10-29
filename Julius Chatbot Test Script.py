# ------------------------------------------------------------
# Julius AI Chatbot Testing Script
# Author: Tori-Ana McNeil
# ------------------------------------------------------------
# PURPOSE:
# Automates testing of the Julius AI chatbot by sending
# multiple prompts, capturing real responses, and evaluating:
#   • Response time
#   • Accuracy (keyword match)
#   • Sentiment / Tone
#
# FIXED:
#   - Detects chatbot inside iframe
#   - Types safely via locator.type()
#   - Captures actual chat replies (not page footer)
#
# NOTES:
#   - The test prompts are made by me and made to test human interaction
#   - All other tests will be implemented soon
#   - The end goal is to be able to test multiple AI models/chatbots,
#     not just Julius and other links.
# ------------------------------------------------------------

from playwright.sync_api import sync_playwright
from textblob import TextBlob
import pandas as pd
import time

# ------------------------------------------------------------
# TEST PROMPTS
# ------------------------------------------------------------
tests = [
    # {"input": "Hello, how are you today?", "expected_keywords": ["hello", "hi", "good", "day", "Unable", "Model", "AI"]},
    {"input": "What is Julius AI capable of doing?", "expected_keywords": ["analyze", "data", "AI", "chatbot"]},
    {"input": "Can you help me write a short poem about autumn?", "expected_keywords": ["poem", "autumn", "fall"]},
    # {"input": "How do I integrate an API into my web app?", "expected_keywords": ["API", "integration", "web", "app"]},
    # {"input": "Tell me a joke.", "expected_keywords": ["joke", "funny", "laugh"]}
]

results = []

# ------------------------------------------------------------
# MAIN TEST LOGIC
# ------------------------------------------------------------
with sync_playwright() as p:
    # Launch browser (set headless=True to hide it)
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("🌐 Opening Julius AI Chatbot...")
    page.goto("https://julius.ai/ai-chatbot", timeout=90000)
    time.sleep(10)  # Allow time for scripts and UI to load

    # Try to accept any cookie/consent popup
    try:
        page.click("button:has-text('Accept')", timeout=3000)
    except:
        pass

    # ------------------------------------------------------------
    # Check for iframe and switch context if chatbot is inside one
    # ------------------------------------------------------------
    print("🔍 Checking for iframe...")
    frames = page.frames
    for frame in frames:
        if "chat" in frame.url or "julius" in frame.url or "bot" in frame.url:
            print(f"🪞 Found iframe: {frame.url}")
            page = frame
            break

    # ------------------------------------------------------------
    # Loop through all test messages
    # ------------------------------------------------------------
    for test in tests:
        message = test["input"]
        expected = [w.lower() for w in test["expected_keywords"]]
        print(f"\n💬 Sending message: {message}")
        start = time.time()

        try:
            # Possible selectors for chat input
            selectors = [
                "div[role='textbox']",
                "div[contenteditable='true']",
                "textarea",
                "input",
                "div[class*='ProseMirror']",
                "[data-placeholder*='Type']",
                "[aria-label*='message']"
            ]

            textbox_found = False
            textbox = None

            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                except:
                    continue

                if page.locator(selector).count() > 0:
                    textbox_found = True
                    textbox = page.locator(selector)
                    print(f"✅ Found input box using selector: {selector}")

                    textbox.click()
                    textbox.fill("")  # clear if needed
                    textbox.type(message)
                    break

            if not textbox_found:
                print("⚠️ Could not find a text input box. Skipping this test.")
                continue

            # Press Enter from inside the textbox
            textbox.press("Enter")

        except Exception as e:
            print(f"⚠️ Error while typing or sending message: {e}")
            continue

        # --- Wait for the AI to respond (takes several seconds) ---
        time.sleep(12)

        # ------------------------------------------------------------
        # Capture bot's reply (with improved selectors)
        # ------------------------------------------------------------
        bot_reply = "No reply detected"
        try:
            # Julius AI uses React-like data-role or markdown elements
            possible_reply_selectors = [
                "div[data-role='assistant']",
                "div[data-testid='assistant-message']",
                "div[class*='assistant']",
                "div[class*='markdown']",
                "div[class*='prose']",
                "div[class*='chat']",
                "div[class*='response']"
            ]

            for sel in possible_reply_selectors:
                if page.locator(sel).count() > 0:
                    all_msgs = page.locator(sel).all_inner_texts()
                    # Filter out empty or repetitive footer text
                    clean_msgs = [m.strip() for m in all_msgs if m.strip() and "Caesar Labs" not in m]
                    if len(clean_msgs) > 0:
                        bot_reply = clean_msgs[-1]
                        break
        except Exception as e:
            print(f"⚠️ Could not extract bot reply: {e}")

        # ------------------------------------------------------------
        # Calculate metrics
        # ------------------------------------------------------------
        end = time.time()
        response_time = round(end - start, 2)

        reply_lower = bot_reply.lower()
        matched = sum(1 for word in expected if word in reply_lower)
        accuracy = round((matched / len(expected)) * 100, 2)

        sentiment = TextBlob(bot_reply).sentiment.polarity
        if sentiment > 0.2:
            tone = "Positive"
        elif sentiment >= -0.2:
            tone = "Neutral"
        else:
            tone = "Negative"

        print(f"🤖 BOT REPLY: {bot_reply[:250]}...")
        print(f"→ Response Time: {response_time}s | Accuracy: {accuracy}% | Tone: {tone}")

        results.append({
            "User Input": message,
            "Bot Reply": bot_reply,
            "Response Time (s)": response_time,
            "Accuracy (%)": accuracy,
            "Tone": tone
        })

    # Close browser after all tests
    browser.close()

# ------------------------------------------------------------
# SAVE RESULTS AND PRINT SUMMARY
# ------------------------------------------------------------
df = pd.DataFrame(results)
df.to_csv("julius_chatbot_results.csv", index=False)

avg_time = df["Response Time (s)"].mean()
avg_accuracy = df["Accuracy (%)"].mean()
tone_counts = df["Tone"].value_counts(normalize=True) * 100

print("\n📊 SUMMARY REPORT")
print(f"Average Response Time: {avg_time:.2f}s")
print(f"Average Accuracy Score: {avg_accuracy:.2f}%")
print("Tone Distribution:")
print(tone_counts.to_string(float_format=lambda x: f'{x:.1f}%'))
print("\n✅ Test completed. Results saved to julius_chatbot_results.csv")
