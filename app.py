import streamlit as st
import os
import requests
from io import BytesIO
from dotenv import load_dotenv
from google import genai

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)
from reportlab.lib.units import inch

# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("Gemini API key not found. Please check your .env file.")
    st.stop()


# Create Gemini client
client = genai.Client(api_key=api_key)
# ==========================================
# PDF GENERATOR
# ==========================================

# ==========================================
# PDF GENERATOR
# ==========================================

def create_pdf(itinerary, destination):

    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        "BulletStyle",
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-8,
        spaceAfter=4
    )

    story = []

    # Title
    story.append(
        Paragraph(
            f"AI Travel Planner - {destination}",
            title_style
        )
    )

    story.append(Spacer(1, 10))

    # Clean itinerary text
    clean_itinerary = itinerary

    # Remove emojis
    emojis = [
        "✈️", "🌍", "🏖️", "🏔️", "🍜", "🏛️",
        "🛍️", "🎉", "🌿", "🏄", "🏨", "🚕",
        "🎟️", "💰", "📍", "📅", "👥"
    ]

    for emoji in emojis:
        clean_itinerary = clean_itinerary.replace(emoji, "")

    # Replace currency symbol
    clean_itinerary = clean_itinerary.replace("₹", "Rs.")

    for line in clean_itinerary.split("\n"):

        line = line.strip()

        # Skip empty lines
        if not line:
            story.append(Spacer(1, 5))
            continue

        # Skip markdown separators
        if line in ["---", "***", "___"]:
            continue

        # Remove markdown headings
        is_heading = False

        if line.startswith("#### "):
            line = line[5:]
            is_heading = True

        elif line.startswith("### "):
              line = line[4:]
              is_heading = True

        elif line.startswith("## "):
              line = line[3:]
              is_heading = True

        elif line.startswith("# "):
              line = line[2:]
              is_heading = True
        # Remove bold markdown
        line = line.replace("**", "")

        # Remove italic markdown
        line = line.replace("__", "")
        line = line.replace("*", "")

        # Bullet points
        if line.startswith("- "):
            line = "• " + line[2:]

            story.append(
                Paragraph(
                    line,
                    bullet_style
                )
            )

        # Headings
        elif is_heading or (
            line[:2].isdigit() and ". " in line[:5]
        ):
            story.append(
                Paragraph(
                    line,
                    heading_style
                )
            )

        # Normal text
        else:
            story.append(
                Paragraph(
                    line,
                    body_style
                )
            )

    document.build(story)

    pdf_buffer.seek(0)

    return pdf_buffer
# ==========================================
# OPENWEATHER API
# ==========================================

weather_api_key = os.getenv("OPENWEATHER_API_KEY")


def get_weather(city):
    """Get current weather information for a city."""

    if not weather_api_key:
        st.error(
            "❌ OpenWeather API key was not found. "
            "Check your .env file."
        )
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": weather_api_key,
        "units": "metric"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 401:
            st.error(
                "❌ OpenWeather API key is invalid or "
                "has not been activated yet."
            )

        elif response.status_code == 404:
            st.error(
                f"❌ Weather information was not found "
                f"for '{city}'."
            )

        else:
            st.error(
                f"❌ OpenWeather API error: "
                f"{response.status_code}"
            )

    except requests.exceptions.RequestException as e:
        st.error(
            f"❌ Could not connect to OpenWeather: {e}"
        )

    return None
# ==========================================
# DESTINATION GEOCODING
# ==========================================

def get_coordinates(city):
    """Get latitude and longitude for a destination."""

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": city,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "AI-Travel-Planner/1.0"
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:

            results = response.json()

            if results:

                latitude = float(results[0]["lat"])
                longitude = float(results[0]["lon"])

                return latitude, longitude

    except requests.exceptions.RequestException:
        pass

    return None
# ==========================================
# CHATBOT SESSION STATE
# ==========================================

if "travel_plan" not in st.session_state:
    st.session_state.travel_plan = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide"
)


# ==========================================
# TITLE
# ==========================================

st.title("✈️ AI Travel Planner")
st.subheader("Plan your perfect trip with AI 🌍")

st.divider()


# ==========================================
# TRIP DETAILS
# ==========================================

st.header("🧳 Tell us about your trip")

col1, col2 = st.columns(2)


with col1:

    destination = st.text_input(
        "📍 Destination",
        placeholder="Example: Goa"
    )

    days = st.number_input(
        "📅 Number of days",
        min_value=1,
        max_value=30,
        value=3
    )

    travelers = st.number_input(
        "👥 Number of travelers",
        min_value=1,
        max_value=20,
        value=2
    )


with col2:

    budget = st.number_input(
        "💰 Total budget (₹)",
        min_value=1000,
        value=15000,
        step=1000
    )

    travel_style = st.selectbox(
        "🎒 Travel style",
        [
            "Budget",
            "Balanced",
            "Luxury",
            "Adventure"
        ]
    )

    interests = st.multiselect(
        "❤️ What are you interested in?",
        [
            "🏖️ Beaches",
            "🏔️ Mountains",
            "🍜 Food",
            "🏛️ History",
            "🛍️ Shopping",
            "🎉 Nightlife",
            "🌿 Nature",
            "🏄 Adventure"
        ]
    )


st.divider()


# ==========================================
# TRIP SUMMARY
# ==========================================

if destination:

    st.header("📊 Trip Summary")

    summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)

    with summary_col1:
        st.metric(
            "📍 Destination",
            destination
        )

    with summary_col2:
        st.metric(
            "📅 Duration",
            f"{days} Days"
        )

    with summary_col3:
        st.metric(
            "👥 Travelers",
            travelers
        )

    with summary_col4:
        st.metric(
            "💰 Total Budget",
            f"₹{budget:,}"
        )

    with summary_col5:

        budget_per_person = budget / travelers

        st.metric(
            "💵 Per Person",
            f"₹{budget_per_person:,.0f}"
        )


    # Daily budget

    budget_per_day = budget / days

    st.info(
        f"💡 Your approximate daily budget is "
        f"**₹{budget_per_day:,.0f}** for the entire group."
    )
        # ==========================================
    # CURRENT WEATHER
    # ==========================================

    st.header("🌤️ Current Weather")

    weather_data = get_weather(destination)

    if weather_data:

        weather_col1, weather_col2, weather_col3, weather_col4 = st.columns(4)

        temperature = weather_data["main"]["temp"]
        feels_like = weather_data["main"]["feels_like"]
        humidity = weather_data["main"]["humidity"]
        wind_speed = weather_data["wind"]["speed"]

        weather_description = weather_data["weather"][0]["description"]

        with weather_col1:
            st.metric(
                "🌡️ Temperature",
                f"{temperature:.1f}°C"
            )

        with weather_col2:
            st.metric(
                "🌡️ Feels Like",
                f"{feels_like:.1f}°C"
            )

        with weather_col3:
            st.metric(
                "💧 Humidity",
                f"{humidity}%"
            )

        with weather_col4:
            st.metric(
                "💨 Wind Speed",
                f"{wind_speed} m/s"
            )

        st.info(
            f"🌤️ **{destination}** currently has "
            f"**{weather_description.title()}**."
        )
    # ==========================================
# DESTINATION MAP
# ==========================================

st.header("🗺️ Destination Map")

coordinates = get_coordinates(destination)

if coordinates:

    latitude, longitude = coordinates

    map_data = {
        "latitude": [latitude],
        "longitude": [longitude]
    }

    st.map(
        map_data,
        zoom=10
    )

    st.caption(
        f"📍 Location shown for **{destination}**"
    )

else:

    st.warning(
        f"⚠️ Could not find the location for {destination}."
    )
    # ==========================================
    # BUDGET BREAKDOWN
    # ==========================================

    st.header("💰 Estimated Budget Breakdown")

    # Percentage allocation

    accommodation_budget = budget * 0.30
    food_budget = budget * 0.20
    transport_budget = budget * 0.15
    activities_budget = budget * 0.20
    miscellaneous_budget = budget * 0.15


    # Budget data for chart

    budget_data = {
        "Category": [
            "Accommodation",
            "Food",
            "Transportation",
            "Activities",
            "Miscellaneous"
        ],
        "Amount": [
            accommodation_budget,
            food_budget,
            transport_budget,
            activities_budget,
            miscellaneous_budget
        ]
    }


    # Budget metrics

    budget_col1, budget_col2 = st.columns(2)


    with budget_col1:

        st.metric(
            "🏨 Accommodation",
            f"₹{accommodation_budget:,.0f}"
        )

        st.metric(
            "🍜 Food",
            f"₹{food_budget:,.0f}"
        )

        st.metric(
            "🚕 Transportation",
            f"₹{transport_budget:,.0f}"
        )


    with budget_col2:

        st.metric(
            "🎟️ Activities",
            f"₹{activities_budget:,.0f}"
        )

        st.metric(
            "🛍️ Miscellaneous",
            f"₹{miscellaneous_budget:,.0f}"
        )

        st.metric(
            "💰 Total",
            f"₹{budget:,.0f}"
        )


    # Budget chart

    st.subheader("📊 Budget Visualization")

    st.bar_chart(
        budget_data,
        x="Category",
        y="Amount"
    )


st.divider()


# ==========================================
# GENERATE TRAVEL PLAN
# ==========================================

if st.button(
    "✨ Generate My Travel Plan",
    use_container_width=True
):

    if not destination:

        st.warning(
            "⚠️ Please enter a destination first."
        )

    else:

        # Convert interests into text

        selected_interests = (
            ", ".join(interests)
            if interests
            else "General sightseeing"
        )

        # ==========================================
        # GEMINI PROMPT
        # ==========================================

        prompt = f"""
You are an expert AI travel planner.

Create a personalized travel plan using these details:

Destination: {destination}
Number of days: {days}
Number of travelers: {travelers}
Total budget: ₹{budget}
Travel style: {travel_style}
Interests: {selected_interests}

Create a practical, realistic and enjoyable itinerary.

Include:

1. Trip Overview
   - Destination
   - Duration
   - Number of travelers
   - Travel style
   - Estimated total budget

2. Day-by-Day Itinerary

For every day include:
- Morning activities
- Afternoon activities
- Evening activities

3. Recommended Places to Visit

4. Food Recommendations

5. Accommodation Suggestions

6. Transportation Suggestions

7. Estimated Budget Breakdown

Break the budget into:
- Accommodation
- Food
- Transportation
- Activities
- Miscellaneous

8. Important Travel Tips

9. Things to Pack

Keep the recommendations suitable for the destination,
number of days, number of travelers and the given budget.

Use clear headings, bullet points and easy-to-read formatting.

Prices, opening hours, availability and transportation
schedules should be treated as estimates unless verified.

Do not claim exact availability, opening hours or
transportation schedules.
"""
        # ==========================================
        # CALL GEMINI
        # ==========================================

        with st.spinner("🤖 AI is planning your trip..."):

            try:

                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt
                )


                # ==========================================
                # DISPLAY RESULT
                # ==========================================

                st.success(
                    "🎉 Your travel plan is ready!"
                )

                st.divider()

                st.header(
                    "🗺️ Your AI Travel Plan"
                )

                st.markdown(
                    response.text
                )


                # Save travel plan for chatbot

                st.session_state.travel_plan = response.text

                # Clear previous chat

                st.session_state.chat_history = []
                
                # ==========================================
                # DOWNLOAD PDF ITINERARY
                # ==========================================

                pdf_file = create_pdf(
                    response.text,
                    destination
                )

                st.download_button(
                    label="📄 Download Travel Itinerary PDF",
                    data=pdf_file,
                    file_name=f"{destination}_Travel_Itinerary.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:

                st.error(
                    f"❌ Something went wrong while "
                    f"generating your trip plan:\n\n{e}"
                )


# ==========================================
# AI TRAVEL CHATBOT
# ==========================================

if st.session_state.travel_plan:

    st.divider()

    st.header("💬 Ask Your AI Travel Assistant")

    st.write(
        "Have questions about your trip? "
        "Ask me anything about your itinerary!"
    )

    # ==========================================
    # DISPLAY CHAT HISTORY
    # ==========================================

    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])


    # ==========================================
    # CHAT INPUT
    # ==========================================

    user_question = st.chat_input(
        "Example: Make Day 2 more budget-friendly..."
    )


    if user_question:

        # Display user message

        with st.chat_message("user"):

            st.markdown(user_question)


        # Save user message

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_question
            }
        )


        # ==========================================
        # CONVERSATION CONTEXT
        # ==========================================

        conversation_context = ""

        for message in st.session_state.chat_history:

            role = message["role"].capitalize()

            conversation_context += (
                f"{role}: {message['content']}\n\n"
            )


        # ==========================================
        # CHATBOT PROMPT
        # ==========================================

        chat_prompt = f"""
You are an AI travel assistant.

Here is the user's current travel itinerary:

{st.session_state.travel_plan}

Here is the previous conversation:

{conversation_context}

The user's latest question is:

{user_question}

Answer the latest question while considering
the travel itinerary and the previous conversation.

Be helpful, practical and concise.

If the user asks to modify the itinerary,
suggest a realistic modification while keeping
their destination, budget and travel preferences
in mind.

If the user refers to something mentioned earlier
in the conversation, use that context to understand
what they mean.

Do not invent exact availability, prices,
opening hours or transportation schedules.

Treat such information as estimates unless verified.
"""


        # ==========================================
        # GENERATE CHAT RESPONSE
        # ==========================================

        with st.chat_message("assistant"):

            with st.spinner("🤖 Thinking..."):

                try:

                    chat_response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=chat_prompt
                    )

                    answer = chat_response.text

                    st.markdown(answer)


                    # Save AI response

                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )


                except Exception as e:

                    st.error(
                        f"❌ Something went wrong: {e}"
                    )
# ==========================================
# RESET TRIP
# ==========================================

st.divider()

if st.button(
    "🔄 Plan a New Trip",
    use_container_width=True
):

    st.session_state.travel_plan = ""

    st.session_state.chat_history = []

    st.rerun()