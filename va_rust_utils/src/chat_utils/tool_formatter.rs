use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::{Captures, Regex};

static TOOL_CALL_PATTERN: Lazy<Regex> =
    Lazy::new(|| Regex::new(r#"\{\s*"([^"]+)"\s*:\s*"((?:\\"|[^"])*)"\s*\}"#).unwrap());

fn replace_tag(caps: &Captures) -> String {
    let tool_type = &caps[1];
    let content = caps[2].replace(r#"\n"#, "\n").replace(r#"\""#, "\"");

    match tool_type {
        "query" => format!("\n```\n{}\n```\n", content),
        "code" => format!("\n```python\n{}\n```\n", content),
        _ => caps[0].to_string(),
    }
}

#[pyfunction]
pub fn chat_utils_tool_formatter_format_tools(text: &str) -> String {
    TOOL_CALL_PATTERN.replace_all(text, replace_tag).to_string()
}
