//! `处理论文引用/分块`
//!
//! # Examples
//! ```rust
//! use crate::academic_utils::paper;
//!
//! paper::attach("1706.03762.md");
//! paper::chunk("1706.03762.md");
//! ```
use pyo3::prelude::*;
use std::collections::HashMap;
use std::fs;
use std::path::{Component, PathBuf};
use std::sync::LazyLock;

/// 论文分块每段最少字节数，经测试，50中文字符/150英文字符分段较平均，语义基本完整
const MIN_BYTE_THRESHOLD: usize = 150;

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

/// 附加文件内容
///
/// 在knowledgeBase和code目录下查找文件。代码文件放入对应代码框中
///
/// # 示例
/// ```
/// attach("1706.03762.md");
/// ```
///
/// # 参数
/// * `file_path`: 文件路径
///
/// # 返回值
/// 文件内容。若为代码则放入代码框。发生任何错误返回空字符串
#[pyfunction]
pub fn attach(file_path: &str) -> String {
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

/// 通过经验判断一行是否是段落
///
/// 本函数假定段落必然包含中文或英文字符和标点符号，且不含#
///
/// # 示例
/// ```
/// is_paragraph("这是一段段落。");
/// ```
///
/// # 参数
/// * `line`: 待判断的行
///
/// # 返回值
/// 若为段落则返回true，否则返回false
fn is_paragraph(line: &str) -> bool {
    let mut has_text = false;
    let mut has_punct = false;
    let mut has_sharp = false;

    for character in line.chars() {
        // 检查中英文字符
        if !has_text {
            has_text =
                character.is_ascii_alphabetic() || ('\u{4e00}'..='\u{9fff}').contains(&character);
        }
        // 检查标点符号
        if !has_punct {
            has_punct = matches!(
                character,
                ',' | '.' | '!' | '?' | ';' | '，' | '。' | '！' | '？' | '；'
            );
        }
        // 检查#
        if !has_sharp {
            has_sharp = character == '#';
        }
        // 提前退出
        if has_text && has_punct && has_sharp {
            return false;
        }
    }
    has_text && has_punct && !has_sharp
}

/// 分段
///
/// 逐行读取并合并，保证每段长度超过150字节(经测试分段较为平均，且基本保证语义完整)。在流式one pass情况下，最大限度确保markdown分段、公式、表格完整
///
/// # 示例
/// ```
/// chunk("1706.03762.md");
/// ```
///
/// # 参数
/// * `file_path`: 文件路径
///
/// # 返回值
/// 分段后的文本
#[pyfunction]
pub fn chunk(file_path: &str) -> Vec<String> {
    let content = attach(file_path);
    let lines = content.trim_matches(['`', ' ', '\n']);
    // 不存在文件/空文件保护
    if lines.is_empty() {
        return Vec::new();
    }
    let line_iter = lines.split('\n');
    let mut temp_string = String::with_capacity(MIN_BYTE_THRESHOLD * 2);
    let mut result_list = Vec::new();
    for line in line_iter {
        let trimmed_line = line.trim();
        // 处理完整段落或空行
        if (trimmed_line.is_empty() || is_paragraph(trimmed_line))
            && temp_string.len() >= MIN_BYTE_THRESHOLD
        {
            // 防止插入额外空行
            if !temp_string.is_empty() {
                // 插入缓存内的字符串，附加额外空行(lines.split不包含换行符)
                result_list.push(temp_string.trim().to_owned());
                temp_string.clear();
                result_list.push("\n".to_owned());
            }
            // 空行情况，需单独插入一个空行，否则LLM大概率忽略，造成markdown格式错误
            if trimmed_line.is_empty() {
                result_list.push("\n".to_owned());
                continue;
            }
        }
        // 高概率非完整段落或字数不够，将该行缓存，添加额外空行(lines.split不包含换行符)
        temp_string.push_str(trimmed_line);
        temp_string.push('\n');
    }
    // 处理边界
    if !temp_string.is_empty() {
        result_list.push(temp_string.trim().to_owned());
    }
    result_list
}
