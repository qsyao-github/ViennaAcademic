//! `处理引用本地文件`
//!
//! # Examples
//! ```rust
//! use crate::chat_utils::attachment_processor;
//!
//! attachment_processor::process_attachments("帮我看一下代码和依赖", ["code.py", "requirements.txt"]);
//! ```
use pyo3::prelude::*;

use crate::academic_utils::paper;

/// 将要引用的文件格式化放到用户输入前
///
/// # 示例
/// ```
/// process_attachments("帮我看一下代码和依赖", ["code.py", "requirements.txt"]);
/// ```
///
/// # 参数
/// * `text`: 用户输入
/// * `file_urls`: 所有引用文件
///
/// # 返回值
/// 处理后文本
#[pyfunction]
pub fn process_attachments(text: &str, file_urls: Vec<String>) -> String {
    let mut new_text = String::with_capacity(512);
    for file in file_urls {
        let content = paper::attach(&file);
        if !content.is_empty() {
            new_text.push_str(&content);
        }
    }
    new_text.push_str(text);
    new_text
}
