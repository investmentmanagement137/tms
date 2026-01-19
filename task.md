# Task: Convert TMS Scraper to Apify Actor

## Project Structure
- [x] Analyze current GitHub Actions workflow
- [x] Analyze current scraper implementation
- [x] Create Apify Actor structure

## Apify Actor Components
- [x] Create `Dockerfile` for Apify Actor
- [x] Create `.actor/actor.json` manifest
- [x] Create `.actor/input_schema.json` for input configuration
- [x] Create `main.py` entry point for Apify
- [x] Update `requirements.txt` for Apify compatibility
- [x] Create `APIFY_README.md` with Apify-specific instructions
- [x] Create `.gitignore` for Apify project
- [x] Create example input file template

# TMS Order Execution Task List

## Planning & Schema
- [x] Add `tmsUrl` to `input_schema.json`
- [x] Remove `get_tms_number` logic

## Implementation
- [x] Update `src/utils.py` (Remove regex logic)
- [x] Update `src/buy_stock.py` to use `tmsUrl`
- [x] Update `src/daily_history.py` to use `tmsUrl`
- [x] Update `main.py` (Pass `tmsUrl` to functions)

## Verification
- [x] Code Structure Verified
- [x] Document Apify Actor setup instructions
- [x] Provide deployment guide
- [x] Document API Usage (curl examples)
- [x] Implement SELL Action and Logic
- [x] Implement Batch Trading (Input Array)
- [x] Add Versioning (Log output)


## GitHub Repository Setup
- [x] Remove hardcoded credentials from trade_book.py
- [x] Configure Git user details
- [x] Resolve merge conflicts
- [x] Push to GitHub repository

## New Features (User Requested)
- [x] **Rewrite Buy/Sell Workflow**
  - [x] Use URL parameters for Symbol (`?symbol=...`)
  - [x] Implement robust JS injection for form filling (Instrument, Toggle, Qty, Price)
  - [x] Verify submit logic
- [x] **Extract Dashboard Data**
  - [x] Implement structured extraction for Fund, Trade, and Collateral summaries
  - [x] Add Market Status detection
  - [x] Fix missing 'Total' values and tooltip noise in extraction
  - [x] Add robust debug logging and HTML/Screenshot capture on failure

