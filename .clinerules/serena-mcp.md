# Serena MCP Server – LLM Usage Rules:

## 1. Activate First
- **Call `serena_activate_project`** with a short, human-readable `project_name`.  
- Cache the returned `project_id`; every later call needs it.

## 2. One Session at a Time
- **Call `serena_create_session`** immediately after activation.  
- Creating a new session silently closes the previous one.  
- If the server restarts, re-activate + re-create session.

## 3. Ingest Before You Ask
- **Use `serena_ingest_files`** with absolute or workspace-relative paths.  
- Supported extensions: `.py .js .ts .java .c .cpp .h .cs .go .rb .php .rs .swift .kt .scala .m .mm .dart .sh .sql .r .R .pl .lua .clj .erl .hs .ml .elm .txt .md .json .xml .yaml .yml`.  
- Re-ingesting the same file updates its content.

## 4. One Question Per Query
- **Pass a single, self-contained question to `serena_query`.**  
- Mention the language explicitly when it matters, e.g., “In the Python files…”.

## 5. Answers Come **Only** from Ingested Files
- If something is missing, Serena will say:  
  “The requested code is not present in the provided files.”

## 6. Nothing Persists After Session Ends
- All indexes disappear on disconnect.  
- Re-ingest files every new session.

## 7. All Calls Are Idempotent
- Safe to retry: re-activating the same project returns the same `project_id`.  
- Re-ingesting unchanged files is a no-op.

## 8. Error Messages Are Actionable
- `File not found: <absolute_path>` → fix the path.  
- `No active session` → run `serena_create_session`.

---

### Quick Flow
1. `serena_activate_project`
2. `serena_create_session`
3. `serena_ingest_files`
4. `serena_query` (repeat 3-4 as needed)