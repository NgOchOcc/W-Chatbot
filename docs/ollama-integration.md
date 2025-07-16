# Ollama Integration Guide

## Overview

This document explains how to integrate Ollama with the W-Chatbot system to replace the default transformers-based question-answering pipeline.

## Prerequisites

1. **Install Ollama**: Follow the official installation guide at https://ollama.ai/
2. **Install aiohttp**: The system now requires `aiohttp` for HTTP requests to Ollama API

## Configuration

### 1. Update Configuration File

Add the following section to your `weschatbot.cfg` file:

```ini
[ollama]
base_url = http://localhost:11434
model = llama3.2
```

### 2. Available Configuration Options

- `base_url`: The URL where Ollama is running (default: http://localhost:11434)
- `model`: The model name to use (default: llama3.2)

## Setup Steps

### 1. Install Dependencies

```bash
pip install aiohttp==3.9.1
```

### 2. Start Ollama Server

```bash
ollama serve
```

### 3. Pull a Model

```bash
# For Llama2 (default)
ollama pull llama3.2

# For other models
```

### 4. Update Configuration

If you want to use a different model, update the `model` parameter in your config:

```ini
[ollama]
base_url = http://localhost:11434
model = mistral  # or any other model you have pulled
```

## How It Works

### Before (Transformers Pipeline)
The system used a BERT-based question-answering pipeline that:
- Took question and context as input
- Used a pre-trained model for extraction-based QA
- Limited to the specific model's training data

### After (Ollama Integration)
The system now uses Ollama which:
- Accepts natural language prompts
- Uses the configured LLM model for generation
- Provides more flexible and context-aware responses
- Supports various models (Llama2, Mistral, CodeLlama, etc.)

### Prompt Structure

The system creates prompts in this format:

```
Based on the following context, answer the question. Only use information from the context provided.

Context:
[Retrieved context from Milvus]

Question: [User's question]

Answer:
```

## Troubleshooting

### Common Issues

1. **Connection Error**: Make sure Ollama server is running on the configured URL
2. **Model Not Found**: Ensure the specified model is pulled using `ollama pull <model_name>`
3. **Timeout Issues**: Large models may take longer to respond; consider using smaller models

### Debug Information

The system logs the prompt being sent to Ollama. Check your application logs for:
```
Ollama prompt: [The full prompt being sent]
```

## Performance Considerations

1. **Model Size**: Larger models provide better responses but are slower
2. **Context Length**: Very long contexts may exceed model limits
3. **Concurrent Requests**: Ollama handles concurrent requests, but performance may degrade with many simultaneous users

## Model Recommendations`

- **General Purpose**: `llama3.2` (default)

## Migration from Transformers

The integration is backward-compatible. The old transformers pipeline is commented out but can be easily restored by:

1. Uncommenting the `qa_pipeline` line
2. Replacing the Ollama call with the original `qa_pipeline` call
3. Removing the Ollama configuration 