# DealFinder AI

This project helps you check whether a car listed on **PakWheels** is **fairly priced** or **undervalued**.  

It works in three steps:  
1. **Scrape data** from PakWheels ads.  
2. **Train a machine learning model** on the scraped data to estimate fair car prices.  
3. **Predict** the expected price of all cars in the dataset (or a single car ad).

You can run this for yourself by reading the instructions and making the changes in the mentioned parts of the code

---

## 1. Web Scraping

Notebook: `PakWheels_webscraper.ipynb`  

- Open the notebook and paste the **PakWheels search URL** (e.g. all Suzuki Mehran ads in Islamabad).  
- The scraper will:  
  - Visit each ad on the search results page.  
  - Collect details (price, mileage, year, etc.).  
  - Save everything into a **CSV file**.  
- You can change:  
  - How many ads to scrape.  
  - Output filename.


`PakWheels_webscraper.ipynb`  
```
#=======================Make Changes Here=======================================
#max no of ads you want to scrap
no_of_ads = 1000

#url for the search page with all the ads
BASE_URL = "https://www.pakwheels.com/used-cars/search/-/ct_islamabad/"

#save file path to save the data
save_path = "Mehran_ads_data.csv"

#===============================================================================
```
---

## 2. Get Results from Complete Data

Notebook: `Data_analysis,_model_training_&_results.ipynb`  

- Open the notebook in Colab.  
- Upload the relevant CSV file to the notebook.  
- The notebook will:  
  - Clean and preprocess the data.  
  - Train a **Random Forest model** to estimate car prices.  
  - Save the trained model and encoder (mlb) in `.pkl` files.  
  - Generate a **results CSV**, sorted by which cars are **listed most below their predicted price** (column: `Price Difference`).  

This helps you quickly see which ads are the **best deals**.  

### Predicting for One Car vs All Cars  

You can control whether to train the model for **one specific car** (e.g. Toyota Corolla) or for **all cars together**:  


`Data_analysis,_model_training_&_results.ipynb`  
```python
#=======================Make Changes Here=======================================

# paste in the path to the csv file containing the data
dataset_path = "/content/Corolla_ads_data.csv"
df = pd.read_csv(dataset_path)

# If you want to train for one car type, set use_all_data = False and specify brand & car.
# If you want to train on ALL cars in the dataset, set use_all_data = True.
use_all_data = False
brand = "Toyota"
car = "Corolla"

#final results with price comparisons file path
save_path = f"{brand}_{car}_results.csv"
#===============================================================================
```

---

## 3. Get Result for One Ad

Notebook: `Single_Car_Price_Predictor.ipynb`  

- Use this if you only want to check the price of a **single car ad**.  
- You need:  
  - A trained model and encoder (mlb) .pkl files (from step 2).
  - url of the ad you want to predict the price for  
- The notebook will load the model and give the **predicted fair price** for that car.  

Tip: Works best when you use the model trained for **one car type** (e.g. only Suzuki Mehran).  

`Single_Car_Price_Predictor.ipynb`  
```python
#==========================Make Changes Here====================================

# Paste the url of the ad
url = "https://www.pakwheels.com/used-cars/toyota-corolla-1997-for-sale-in-islamabad-10429613"

# paste the model and mlb path for either the specific car or all cars
model = joblib.load("Toyota_Corolla_model.pkl")
mlb = joblib.load("Toyota_Corolla_mlb.pkl")

#===============================================================================
```
---

## Example Data and Models

- Sample datasets and models for **Suzuki Mehran** and **Toyota Corolla** are included in:  
  - `data/`  
  - `models/`  
  - `results/` 
