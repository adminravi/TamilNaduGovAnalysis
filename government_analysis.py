import feedparser
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import datetime
import time
import os

# Path to the Feedback CSV File
feedback_file = "corrected_labels.csv"

# Define Search Queries for Governance News
search_queries = {
    "Govt Analysis": [
        "https://news.google.com/rss/search?q=Tamil+Nadu+government+failure+OR+misgovernance+OR+corruption+OR+controversy&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=Tamil+Nadu+government+success+OR+achievement+OR+development+OR+growth&hl=en-IN&gl=IN&ceid=IN:en"
    ],
    "Protests Against Government": [
        "https://news.google.com/rss/search?q=Tamil+Nadu+protest+OR+strike+OR+agitation+OR+movement+OR+demonstration+OR+rally&hl=en-IN&gl=IN&ceid=IN:en"
    ]
}

# Function to Classify News Sentiment
def classify_governance_sentiment(text, category):
    """Classify news as Good Governance, Misgovernance, or Protest based on keywords."""
    
    if category == "Govt Analysis":
        if any(word in text.lower() for word in ["failure", "misgovernance", "corruption", "controversy"]):
            return "Misgovernance (TN Govt Only)"
        elif any(word in text.lower() for word in ["success", "achievement", "development", "growth"]):
            return "Good Governance (TN Govt Only)"
    
    elif category == "Protests Against Government":
        if "dmk" in text.lower() or "stalin" in text.lower() or "tamil nadu government" in text.lower():
            return "Anti TN State Government"
        elif "modi" in text.lower() or "bjp government" in text.lower() or "central government" in text.lower():
            return "Anti Central Government"
        else:
            return "General Protest"
    
    return None  # If no category matches, return None

# Enable caching to reduce API calls
@st.cache_data(ttl=1800)
def fetch_news(selected_category, days_filter):
    all_news = set()
    news_data = []

    for rss_url in search_queries[selected_category]:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            published_date = datetime.datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
            days_ago = (datetime.datetime.utcnow() - published_date).days

            if days_ago <= days_filter:
                if entry.title not in all_news:
                    sentiment_label = classify_governance_sentiment(entry.title, selected_category)
                    if sentiment_label:
                        all_news.add(entry.title)
                        news_data.append({
                            "Category": selected_category,
                            "Title": entry.title,
                            "Published Date": published_date.date(),
                            "URL": entry.link,
                            "Sentiment": sentiment_label
                        })
                time.sleep(0.5)
    
    return pd.DataFrame(news_data, columns=["Category", "Title", "Published Date", "URL", "Sentiment"])

# Load Feedback File
if os.path.exists(feedback_file):
    try:
        feedback_df = pd.read_csv(feedback_file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        feedback_df = pd.read_csv(feedback_file, encoding="ISO-8859-1")
else:
    feedback_df = pd.DataFrame(columns=["Title", "Corrected Sentiment"])

# Streamlit Dashboard
st.set_page_config(page_title="Tamil Nadu Govt Analysis", layout="wide")
st.title("📊 Tamil Nadu Government Analysis")

# Tab Navigation for Faster Access
tab1, tab2 = st.tabs(["Govt Analysis", "Protests Against Government"])

# Time Period Selection Dropdown
time_options = {
    "Today": 1,
    "Last 10 Days": 10,
    "Last 30 Days": 30,
    "Last 60 Days": 60,
    "Last 90 Days": 90
}

with tab1:
    st.subheader("Govt Analysis")
    
    # Time selection for Govt Analysis
    selected_time = st.selectbox("Select Time Period:", list(time_options.keys()), key="govt_analysis_time")
    selected_category = "Govt Analysis"
    df_selected = fetch_news(selected_category, time_options[selected_time])
    df_selected = df_selected[df_selected["Sentiment"].isin(["Good Governance (TN Govt Only)", "Misgovernance (TN Govt Only)"])]

    sentiment_counts = df_selected["Sentiment"].value_counts()
    
    if not df_selected.empty:
        fig, ax = plt.subplots()
        ax.pie(sentiment_counts, labels=sentiment_counts.index, autopct="%1.1f%%", startangle=90)
        plt.title("Government Performance Analysis")
        st.pyplot(fig)
    
        st.write("### 📰 Click on a headline to read the full article:")

        for _, row in df_selected.iterrows():
            st.markdown(f"📌 **[{row['Title']}]({row['URL']})**  -  {row['Sentiment']}", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No relevant news articles found for the selected time period.")

with tab2:
    st.subheader("Protests Against Government")
    
    # Time selection for Protests Analysis
    selected_time = st.selectbox("Select Time Period:", list(time_options.keys()), key="protest_time")
    selected_category = "Protests Against Government"
    df_selected = fetch_news(selected_category, time_options[selected_time])
    df_selected = df_selected[df_selected["Sentiment"].isin(["Anti TN State Government", "Anti Central Government", "General Protest"])]

    sentiment_counts = df_selected["Sentiment"].value_counts()
    
    if not df_selected.empty:
        # Create two columns for side-by-side display
        col1, col2 = st.columns(2)

        # **Protests Analysis Pie Chart (Left)**
        with col1:
            st.subheader("📊 Protests Analysis")
            fig, ax = plt.subplots()
            ax.pie(sentiment_counts, labels=sentiment_counts.index, autopct="%1.1f%%", startangle=90)
            plt.title("Protests Breakdown")
            st.pyplot(fig)

        # **Protest Trends Over Time Graph (Right)**
        with col2:
            st.subheader("📈 Protest Trends Over Time")
            df_selected["Published Date"] = pd.to_datetime(df_selected["Published Date"])
            protest_trend = df_selected.groupby(["Published Date", "Sentiment"]).size().unstack().fillna(0)

            fig, ax = plt.subplots(figsize=(6, 4))
            protest_trend.plot(ax=ax, marker='o')
            ax.set_title(f"Protest Trends Over {selected_time}")
            ax.set_xlabel("Date")
            ax.set_ylabel("Number of Protest News Articles")
            ax.legend(title="Type of Protest")

            st.pyplot(fig)

        st.write("### 📰 Click on a headline to read the full article:")

        for _, row in df_selected.iterrows():
            st.markdown(f"📌 **[{row['Title']}]({row['URL']})**  -  {row['Sentiment']}", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No protest data available for the selected time period.")

# Editable Table for Manual Sentiment Correction
st.subheader("📝 Edit and Save Sentiment Corrections")
feedback_df = st.data_editor(feedback_df, num_rows="dynamic")
if st.button("Save Corrections"):
    feedback_df.to_csv(feedback_file, index=False)
    st.success("Corrections Saved Successfully")

st.write("✅ Dashboard Updates Every Few Minutes!")
