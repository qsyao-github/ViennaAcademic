//! `识别模型生成的工具调用并重新排版`
//!
//! # Examples
//! ```rust
//! use crate::chat_utils::tool_formatter;
//!
//! tool_formatter::chat_utils_tool_formatter_format_tools(r#"{ \n "tool_name": \n "arg_name""#);
//! ```
use pyo3::prelude::*;
use regex::{Captures, Regex};
use std::process;
use std::sync::LazyLock;

/// 匹配json格式工具调用
///
/// # 示例
/// ```
/// TOOL_CALL_PATTERN.replace_all(text, replace_tag).to_string();
/// ```
pub static TOOL_CALL_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"\{\s*"([^"]+)"\s*:\s*"((?:\\"|[^"])*)"\s*\}"#).unwrap_or_else(|_| {
        process::exit(1);
    })
});

/// 替换工具调用内容
///
/// 匹配工具名称及参数，并调用TOOLS中对应的函数，将整体替换为结果
///
/// # 参数
/// * `match`: 匹配结果
///
/// # 返回值
/// 替换后的文本
fn replace_tag(caps: &Captures) -> String {
    let tool_type = &caps[1];
    let content = caps[2].replace(r"\n", "\n").replace(r#"\""#, "\"");

    match tool_type {
        "query" => format!("\n```\n{content}\n```\n"),
        "code" => format!("\n```python\n{content}\n```\n"),
        _ => caps[0].to_string(),
    }
}

/// 工具调用排版
///
/// # 示例
/// ```
/// chat_utils_tool_formatter_format_tools(r#"{ \n "tool_name": \n "arg_name""#);
/// ```
///
/// # 参数
/// * `text`: 待处理文本
///
/// # 返回值
/// 处理后文本
#[pyfunction]
pub fn chat_utils_tool_formatter_format_tools(text: &str) -> String {
    TOOL_CALL_PATTERN.replace_all(text, replace_tag).to_string()
}
