#!/bin/bash
# Script to clear the AI Career Agent database for fresh start

echo "Clearing AI Career Agent database..."

# Remove main SQLite database
rm -f /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/career_agent.db
echo "✓ Removed main database: career_agent.db"

# Remove ChromaDB embedding databases
rm -f /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/embeddings/career/chroma.sqlite3
rm -f /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/embeddings/applications/chroma.sqlite3
rm -f /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/embeddings/jobs/chroma.sqlite3
echo "✓ Removed embedding databases"

# Remove test databases
rm -f /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/test_debug.db
rm -f /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/test_debug2.db
echo "✓ Removed test databases"

# Remove ChromaDB collections directories (they will be recreated)
rm -rf /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/embeddings/career/*
rm -rf /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/embeddings/applications/*
rm -rf /Users/sharma.rajasekar/PycharmProjects/AI_Career_Agent_for_Senior_IT_Leaders/app/data/embeddings/jobs/*
echo "✓ Cleared embedding collection directories"

echo "Database cleared successfully! You can now start the application fresh."