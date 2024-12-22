# 3. **Создание приложения на Streamlit**:
#    - Добавить интерфейс для загрузки файла с историческими данными.
#    - Добавить интерфейс для выбора города (из выпадающего списка).
#    - Добавить форму для ввода API-ключа OpenWeatherMap. Когда он не введен, данные для текущей погоды не показываются. Если ключ некорректный, выведите на экран ошибку (должно приходить `{"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}`).
#    - Отобразить:
#      - Описательную статистику по историческим данным для города, можно добавить визуализации.
#      - Временной ряд температур с выделением аномалий (например, точками другого цвета).
#      - Сезонные профили с указанием среднего и стандартного отклонения.
#    - Вывести текущую температуру через API и указать, нормальна ли она для сезона.

from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

def request_current_temperature_for_city(city, token):
    resp = requests.get("https://api.openweathermap.org/data/2.5/weather", {"q": city, "units": "metric", "appid": token})
    
    if resp.status_code == 200:
        return resp.json()["main"]["temp"]
    else:
        raise Exception(resp.json()["message"])

def handle_data(data):
    # convert timestamp to datetime
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # detect anomalies
    data['temp_seasonal_mean'] = data.groupby(['city', 'season'])['temperature'].transform('mean')
    data['temp_seasonal_std'] = data.groupby(['city', 'season'])['temperature'].transform('std')
    data['anomaly'] = (data['temperature'] > data['temp_seasonal_mean'] + 2 * data['temp_seasonal_std']) | (data['temperature'] < data['temp_seasonal_mean'] - 2 * data['temp_seasonal_std'])

    # rolling mean
    data['temp_rolling_mean'] = data.groupby('city')['temperature'].transform(lambda x: x.rolling(window=30, min_periods=1).mean())

    return data  

def is_temperature_anomaly(city_data, city, season, temp):
  city_season_data = city_data[city_data['season'] == season]

  seasonal_mean = city_season_data['temp_seasonal_mean'].values[0]
  seasonal_std = city_season_data['temp_seasonal_std'].values[0]

  return temp > seasonal_mean + 2*seasonal_std or temp < seasonal_mean - 2*seasonal_std

st.title("Weather App")

# File upload   
file = st.file_uploader("Upload file", type=["csv"])
if file is not None:
    data = pd.read_csv(file)

    city = st.selectbox("Select city", data["city"].unique())
    city_data = handle_data(data[data["city"] == city])

    # Show info about city
    st.write(f"{city} temperature stats")
    st.write(city_data['temperature'].describe())

    # Plot temperature with anomalies and rolling mean with matplotlib
    st.write(f"{city} temperature with anomalies and rolling mean")
    
    fig, ax = plt.subplots()
    
    ax.plot(city_data['timestamp'], city_data['temperature'], label="Temperature", color='skyblue')
    ax.plot(city_data['timestamp'], city_data['temp_rolling_mean'], label="Rolling mean", color='orange')
    ax.scatter(city_data[city_data['anomaly']]['timestamp'], city_data[city_data['anomaly']]['temperature'], color='red', label="Anomaly")

    ax.legend()
    ax.set_xlabel("Year")
    ax.set_ylabel("Temperature")

    st.pyplot(fig)

    # Seasonal profiles using season, temp_seasonal_mean and temp_seasonal_std
    st.write(f"{city} seasonal profiles")

    season_profile = city_data.groupby(['season'])[['temp_seasonal_mean', 'temp_seasonal_std']].first().reset_index()

    fig, ax = plt.subplots()

    ax.errorbar(
        season_profile['season'], 
        season_profile['temp_seasonal_mean'], 
        yerr=season_profile['temp_seasonal_std'], 
        fmt='o', 
        capsize=10,
        label="Mean ± 2 std"
    )

    ax.legend()
    ax.set_xlabel("Season")
    ax.set_ylabel("Temperature")

    st.pyplot(fig)

month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

# API key
api_key = st.text_input("Enter OpenWeatherMap API key to check current temperature")
if api_key and file is not None:    
    try:
        current_temperature = request_current_temperature_for_city(city, api_key)
        st.write(f"Current temperature in {city} is {current_temperature}°C")

        # Check if current temperature is anomaly
        current_season = month_to_season[datetime.now().month]
        is_anomaly = is_temperature_anomaly(city_data, city, current_season, current_temperature)

        if is_anomaly:
            st.warning(f"Current temperature is anomaly for {current_season}")
        else:
            st.success(f"Current temperature is normal for {current_season}")

    except Exception as e:
        st.error(e)

