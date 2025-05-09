# Freqtrade Copilot V2

An LLM-powered interface for interacting with the Freqtrade API using natural language. This tool allows you to control and query your Freqtrade trading bot using plain English commands, powered by OpenAI's language models.

## Overview

Freqtrade Copilot V2 connects OpenAI's API with Freqtrade's REST API, enabling seamless interaction with your trading bot using natural language. The copilot can:

- Check the status of your trades
- Get account balance
- View performance metrics
- Manage bot operations (start, stop, pause)
- Execute trades
- And more!

## Requirements

- Python 3.8+
- Running Freqtrade instance with API enabled
- OpenAI API key

## Installation

1. Make sure you have a running Freqtrade instance with the API server enabled in your `config.json`.

2. Install the required packages:
   ```
   pip install openai python-dotenv
   ```

3. Copy the `.env.example` file to `.env` and add your OpenAI API key:
   ```
   cp user_data/copilot_v2/.env.example user_data/copilot_v2/.env
   ```

4. Edit the `.env` file with your specific configuration if needed.

## Usage

Run the copilot from your Freqtrade directory. There are two ways to run it:

### Option 1: Run directly as a script
```
python user_data/copilot_v2/run.py
```

### Option 2: Run as a module (recommended Python best practice)
```
python -m user_data.copilot_v2.run
```

Both methods will work, but running as a module is more aligned with Python's package import system.

### Command line options

```
python user_data/copilot_v2/run.py --help
```
or
```
python -m user_data.copilot_v2.run --help
```

Available options:
- `--model`: OpenAI model to use (default: o3)
- `--api-url`: Freqtrade API URL (defaults to environment variable or http://127.0.0.1:8080)
- `--username`: Freqtrade API username (defaults to environment variable or "a")
- `--password`: Freqtrade API password (defaults to environment variable or "a")

### Example Conversations

Here are some examples of how you can interact with the copilot:

```
🤖 > What's the current status of my bot?

// The copilot will call the status API and display the current trades

🤖 > Show me my account balance

// The copilot will retrieve and display your account balance

🤖 > How is the performance of my trades?

// The copilot will retrieve performance metrics and display them

🤖 > Pause the bot

// The copilot will send a command to pause the bot

🤖 > Buy some Bitcoin

// The copilot will guide you through making a forcebuy for BTC
```

## Special Commands

- `exit` or `quit`: End the session
- `clear`: Clear the conversation history and start fresh

## Project Structure

- `run.py`: Main script to run the copilot
- `api/gateway.py`: Handles communication between OpenAI and Freqtrade API
- `tools/rest_adapter.py`: Implements all the API calls to Freqtrade
- `tools/function_tools.py`: Defines the function schemas for OpenAI tool calling

## Customization

You can modify the system message in `api/gateway.py` to change the personality or behavior of the assistant.

## Troubleshooting

- Make sure your Freqtrade instance is running and the API is enabled
- Check that your API credentials in the `.env` file match those in your Freqtrade `config.json`
- Verify your OpenAI API key is valid and has sufficient credits

## License

Same as Freqtrade. See the main project for details.
