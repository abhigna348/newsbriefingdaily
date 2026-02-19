# NewsBriefingDaily

Type a topic → get a spoken news summary powered by AI.

---

## What it does

1. You type a prompt like `"give me top news in politics"`
2. It fetches today's headlines
3. GPT summarizes them
4. Plays it as audio

---

## Setup

**Install:**
```bash
pip install openai requests streamlit
```

**Add your API keys:**
- OpenAI → https://platform.openai.com/api-keys
- NewsAPI (free) → https://newsapi.org/register

---

## Run

**Jupyter:**
- Open `ai_news_briefing.ipynb`
- Run Cell 1–5 once, then use Cell 6

**Web app:**
```bash
streamlit run app.py
```

---

## Supported topics

`politics` `tech` `business` `health` `sports` `science` `entertainment` `world`
