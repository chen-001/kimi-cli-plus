Use this tool when you need the user to make a choice or provide input.

**CRITICAL: When you have multiple options for the user to choose from, you MUST call this tool. DO NOT list options in your response.**

## MANDATORY Use Cases

You MUST call AskUser in these situations:

1. **User asks for options** - "give me options", "what are my choices", "which one should I pick"
2. **Multiple approaches available** - 2+ ways to accomplish a task
3. **Need user decision** - Clarification required before proceeding
4. **User must provide input** - Need specific information to continue

## How to Use

```json
{
  "questionnaire": "Please choose an approach:\n\n[question] Which approach do you prefer?\n[topic] Approach\n[option] Option A: Fast solution\n[option] Option B: Thorough solution"
}
```

**Format for `questionnaire` field:**
- `[question]` - The main question to ask
- `[topic]` - Short label for UI navigation (optional)
- `[option]` - Each option on its own line

The user can:
1. Use UP/DOWN arrows to navigate options
2. Press ENTER to select
3. Type custom input when "✏️ 自定义输入" option is selected

**Note:** The system automatically adds a "✏️ 自定义输入" option at the end of the list. You don't need to add it manually.

## Examples

**User: "I want to optimize my code, give me some options"**

Call AskUser with:
```json
{
  "questionnaire": "[question] Which optimization approach would you like?\n[topic] Optimization\n[option] Speed optimization\n[option] Memory optimization\n[option] Readability improvement"
}
```

**User: "How should I handle authentication?"**

Call AskUser with:
```json
{
  "questionnaire": "[question] Which authentication method do you prefer?\n[topic] Auth Method\n[option] OAuth 2.0\n[option] JWT tokens\n[option] Session-based"
}
```

## Important

- ALWAYS call AskUser when you have options to present
- NEVER list options in your text response
- The tool provides an interactive selection UI with keyboard navigation
- **The system automatically adds a "✏️ 自定义输入" option at the end** - you don't need to add it manually
