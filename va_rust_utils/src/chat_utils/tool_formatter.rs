use pyo3::prelude::*;
use regex::{Captures, Regex};

pub static TOOL_CALL_PATTERN: std::sync::LazyLock<Regex> = std::sync::LazyLock::new(|| {
    Regex::new(r#"\{\s*"([^"]+)"\s*:\s*"((?:\\"|[^"])*)"\s*\}"#).unwrap()
});

/*
替换工具调用内容

匹配工具名称及参数，并调用TOOLS中对应的函数，将整体替换为结果

Parameters
----------
match: &Captures
    匹配结果

Returns
----------
String
    替换后的文本
*/
fn replace_tag(caps: &Captures) -> String {
    let tool_type = &caps[1];
    let content = caps[2].replace(r"\n", "\n").replace(r#"\""#, "\"");

    match tool_type {
        "query" => format!("\n```\n{content}\n```\n"),
        "code" => format!("\n```python\n{content}\n```\n"),
        _ => caps[0].to_string(),
    }
}

/*
工具调用排版

Parameters
----------
text: &str
    待处理文本

Returns
----------
String
    处理后文本
*/
#[pyfunction]
pub fn chat_utils_tool_formatter_format_tools(text: &str) -> String {
    TOOL_CALL_PATTERN.replace_all(text, replace_tag).to_string()
}
