
import json
import streamlit as st
from datetime import date, timedelta

# Load crop information
with open("crops.json", "r", encoding="utf-8") as file:
    crop_data = json.load(file)

# Growing milestones (illustrative proportions)
milestones = [
    ("🌱", "Planting", 0),
    ("🌿", "Germination", 0.10),
    ("🌾", "Early growth", 0.25),
    ("🌳", "Vegetative growth", 0.50),
    ("🌼", "Reproductive development", 0.70),
    ("🌻", "Maturity", 0.90),
    ("🌾", "Harvest", 1.00)
]

st.set_page_config(page_title="My Growing Timeline",
                   page_icon="🌱")

st.title("🌱 My Growing Timeline")
st.write("Create a timeline for your planted crops.")

# Crop selection
available_crops = [
    name for name in crop_data
    if isinstance(crop_data[name], dict)
    and "season_length_days" in crop_data[name]
]

crop = st.selectbox("Select your crop", available_crops)

# Planting information
planting_date = st.date_input(
    "Planting date",
    value=date.today()
)

location = st.text_input(
    "Planting location",
    placeholder="e.g. Field A"
)

# Generate timeline
if st.button("Generate timeline"):

    season_length = crop_data[crop]["season_length_days"]

    harvest_date = planting_date + timedelta(
        days=season_length
    )

    st.divider()

    st.header(f"🌱 {crop.title()} Growing Journey")

    st.write(f"📍 Location: {location}")
    st.write(f"📅 Planted: {planting_date}")

    st.success(
        f"Estimated harvest: {harvest_date}"
    )

    st.subheader("Your Crop Timeline")

    for emoji, stage, proportion in milestones:

        stage_date = planting_date + timedelta(
            days=round(season_length * proportion)
        )

        st.markdown(f"""
        ### {emoji} {stage}

        **{stage_date.strftime('%d %B %Y')}**

        """)
        st.progress(proportion)

    st.caption(
        "Growth milestones are illustrative estimates. "
        "Actual crop development depends on variety, "
        "climate and local growing conditions."
    )
