# Overview

Welcome to the Chatbot Management System documentation. This overview describes the goals, architecture, core
components, workflows, and key features of the platform.

## Objectives

- Provide a unified web interface to administer every aspect of your chatbot infrastructure
- Enable full lifecycle management of users, chat sessions, RAG documents, vector collections, and chatbot parameters
- Enforce Role-Based Access Control (RBAC) to secure operations across different operator roles

## System Architecture

The Chatbot Management System is comprised of five layers:

1. **Frontend**
    - Built with React and CoreUI
    - Responsive UI for dashboards, tables, forms, and detail views
2. **Backend API**
    - Flask application exposing REST endpoints
    - Handles authentication, authorization, business logic, and file processing
3. **Metadata Database**
    - MySQL stores users, sessions, documents, configurations, and RBAC models
4. **Vector Store**
    - Milvus as the embedding index
    - Stores and searches vector representations of uploaded documents
5. **Embedding & RAG Engine**
    - Embedding model (e.g. Qwen3-Embedding-0.6B) converts Markdown content and queries into vectors
    - Retrieval-Augmented Generation (RAG) assembles context from top results and invokes the LLM(self-hosted by vLLM)

## Core Components

- **User**  
  Represents an operator account (admin or standard user) with profile data and assigned role.
- **Chat Session**  
  Records each conversation between a user and the chatbot, including timestamps and message history.
- **Document**  
  Files uploaded to the system (PDF, DOCX, TXT), automatically converted into Markdown and indexed.
- **Collection**  
  A named Milvus collection that groups document embeddings; supports indexing, flushing, and deletion.
- **Configuration**  
  Chatbot settings such as the system prompt template, target collection for RAG, and similarity threshold.
- **RBAC**  
  Defines roles and permissions to control access to each management function.

## Workflow

1. **Document Ingestion**
    - Admin uploads a file → system converts pages into Markdown → embeds content → stores vectors in Milvus
2. **Query Processing**
    - User submits a question → system encodes the query → retrieves nearest neighbors from the Milvus collection
3. **Response Generation**
    - Retrieved chunks are combined into a prompt with the system template → sent to the LLM → answer returned to the
      user
4. **Session & Audit**
    - Each interaction is stored as a chat session for review or deletion by authorized users

## Key Features

- Intuitive, role-aware UI for CRUD operations on users, sessions, documents, collections, and configs
- Automatic Markdown conversion with syntax support for tables, code blocks, and images
- Seamless Milvus integration for high-performance vector search
- Pluggable embedding models and configurable similarity metric (Cosine or IP)
- Fine-grained RBAC ensures only authorized roles can perform sensitive actions

This overview should orient you to the system’s purpose and structure. Refer to the individual chapters for step-by-step
guides on each module. ```