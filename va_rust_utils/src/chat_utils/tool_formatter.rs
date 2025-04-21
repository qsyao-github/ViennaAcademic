use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::{Captures, Regex};

pub static TOOL_CALL_PATTERN: Lazy<Regex> =
    Lazy::new(|| Regex::new(r#"\{\s*"([^"]+)"\s*:\s*"((?:\\"|[^"])*)"\s*\}"#).unwrap());

fn replace_tag(caps: &Captures) -> String {
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
    TOOL_CALL_PATTERN.replace_all(text, replace_tag).to_string()
}
