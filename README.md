# EECS4312_W26_SpecChain
## Application: Calm
ID: com.calm.android
Company: Calm.com, Inc.
Packages needed: see requirements.txt

## Dataset:
```
- ./data/reviews_raw.jsonl        Contains the collected reviews
- ./data/reviews_clean.jsonl      Contains the cleaned dataset
```
- The cleaned dataset contains 1678 reviews.
- The actual review count was 605K, making sampling a hard requirement, thus we collected 2000 raw, which is perfectly enough for our tracking purposes and cleaned to 1678.

## Repository Structure:
```
- data/                      contains datasets and review groups
- personas/                  contains persona files
- spec/                      contains specifications
- tests/                     contains validation tests
- metrics/                   contains all metric files
- src/                       contains executable Python scripts
- reflection/                contains the final reflection
```

## Setting Up Your System
Before even attempting to run the system, please make sure you have Python installed and the packages required to run this system:

```pip install -r requirements.txt```

After you have the dependencies installed, please create a file called ```.env``` at root and insert the key as this format:
```
#Create a .env (exact name) and put GROQ_API_KEY below 
<key goes here - make sure your key is exactly the key give by Groq>
```

example:
```
#GROQ_API_KEY
gsk_...........
```
After you have properly configured everything you may continue to the steps below:

## How to Run:
1. Run the program by either entering python src/run_all.py in a terminal connected to root or run run_all.py on an IDE (I simplified all the steps to run every task)
2. After running the program you should have validated all your files and ran all the tasks needed
3. Open metrics/metrics_summary.json for comparison results

## LLM Model Disclaimer
All autogeneration details and info used the Groq API with model:
meta-llama/llama-4-scout-17b-16e-instruct

### WARNING! IF YOU ARE MISSING FILES THE SYSTEM WILL HALT OPERATION UNTIL YOU REGAIN ALL FILES