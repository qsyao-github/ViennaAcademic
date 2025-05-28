//! `处理论文引用/分块`
//!
//! # Examples
//! ```rust
//! use crate::academic_utils::paper;
//!
//! paper::academic_utils_paper_attach("1706.03762.md");
//! paper::academic_utils_paper_chunk("1706.03762.md");
//! ```
use core::mem;
use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::path::{Component, PathBuf};
use std::process;
use std::sync::LazyLock;

/// 论文分块每段最少字符数
const MIN_CHARACTER_THRESHOLD: usize = 63;

/// 根据文件类型后缀映射到markdown代码框的类型
///
/// 支持主流编程语言
///
/// # 示例
/// ```
/// SUFFIX_MAP.get("py");
/// ```
pub static SUFFIX_MAP: LazyLock<HashMap<&str, &str>> = LazyLock::new(|| {
    HashMap::from([
        ("py", "python"),
        ("c", "c"),
        ("cpp", "cpp"),
        ("md", "markdown"),
        ("json", "json"),
        ("html", "html"),
        ("css", "css"),
        ("js", "javascript"),
        ("jinja2", "jinja2"),
        ("ts", "typescript"),
        ("yaml", "yaml"),
        ("dockerfile", "dockerfile"),
        ("sh", "shell"),
        ("r", "r"),
        ("sql", "sql"),
    ])
});

/// 匹配任何空行
///
/// # 示例
/// ```
/// LINEBREAK_RE.split("Line1  \n\n  Line2");
/// ```
pub static LINEBREAK_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\s*\n+\s*").unwrap_or_else(|_| {
        process::exit(1);
    })
});

/// 附加文件内容
///
/// 在knowledgeBase和code目录下查找文件。代码文件放入对应代码框中
///
/// # 示例
/// ```
/// academic_utils_paper_attach("1706.03762.md");
/// ```
///
/// # 参数
/// * `file_path`: 文件路径
///
/// # 返回值
/// 文件内容。若为代码则放入代码框。发生任何错误返回空字符串
#[pyfunction]
pub fn academic_utils_paper_attach(file_path: &str) -> String {
    let trimmed_path = PathBuf::from(file_path.trim_start_matches('/'));
    // 构建知识库文件路径
    let mut components: Vec<_> = trimmed_path.components().collect();
    if components.len() != 4 {
        return String::new();
    }
    if let Some(comp) = components.get_mut(2) {
        if *comp == Component::Normal("paper".as_ref()) {
            *comp = Component::Normal("knowledgeBase".as_ref());
            let mut kb_path: PathBuf = components.iter().collect();
            kb_path.set_extension("md");
            if let Ok(content) = fs::read_to_string(&kb_path) {
                return format!("```\n{content}\n```\n\n");
            }
        }
        return String::new();
    }

    // 检查并读取代码文件
    if let Ok(content) = fs::read_to_string(&trimmed_path) {
        let lang = trimmed_path
            .extension()
            .and_then(|ext| ext.to_str())
            .and_then(|ext| SUFFIX_MAP.get(ext))
            .copied()
            .unwrap_or("");

        return format!("```{lang}\n{content}\n```\n\n");
    }
    String::new()
}

/// 分段
///
/// 按换行符分段，确保每段长度大于63个字符
///
/// # 示例
/// ```
/// academic_utils_paper_chunk("1706.03762.md");
/// ```
///
/// # 参数
/// * `file_path`: 文件路径
///
/// # 返回值
/// 分段后的文本
#[expect(
    clippy::arithmetic_side_effects,
    reason = "文本长度不会超过usize::MAX，不会溢出"
)]
#[pyfunction]
pub fn academic_utils_paper_chunk(file_path: &str) -> Vec<String> {
    let content = academic_utils_paper_attach(file_path);
    let mut final_list = Vec::new();
    let mut temp_string = String::with_capacity(MIN_CHARACTER_THRESHOLD * 2);
    let mut char_count = 0;

    for para in LINEBREAK_RE.split(&content) {
        let para_len = para.chars().count();
        temp_string.push_str(para);
        char_count += para_len;
        if char_count > MIN_CHARACTER_THRESHOLD {
            final_list.push(mem::take(&mut temp_string));
            char_count = 0;
            continue;
        }
        temp_string.push_str("\n\n");
    }

    final_list.push(temp_string);

    final_list
}
