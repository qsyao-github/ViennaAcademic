//! `arxiv_crawler.py的html解析，markdown格式化的较高性能实现`
//!
//! # Examples
//! ```rust
//! use crate::web_utils::arxiv_crawler;
//!
//! arxiv_crawler::web_utils_arxiv_crawler_process_markdown("[[13](some_link)]\n\n\n");
//! ```

use pyo3::prelude::*;
use regex::Regex;
use std::process;
use std::sync::LazyLock;

/// 匹配引用超链接或连续空行
///
/// # 示例
/// ```
/// COMBINED_REGEX
///     .replace_all(markdown_content, |caps: &regex::Captures| {
///         caps.get(1).map_or_else(
///             || "\n\n".to_owned(),
///             |link_text| format!("[{}]", link_text.as_str()),
///         )
///     });
/// ```
///
/// # Notes
/// 当匹配到链接时，匹配组是引用标号。当匹配到连续空行时，匹配组为空。据此分别处理。
static COMBINED_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\[{1,2}([^\]]*)\]\([^)]*\)\]?|\n{3,}").unwrap_or_else(|_| {
        process::exit(1);
    })
});

/// 提取Arxiv论文正文部分
///
/// # 示例
/// ```
/// web_utils_arxiv_crawler_extract_article("<some_tag><article>article content</article></some_tag>");
/// ```
///
/// # 参数
/// * `html`: arxiv原始html
///
/// # 返回值
/// html内的文章内容
#[expect(
    clippy::arithmetic_side_effects,
    clippy::string_slice,
    reason = "由于文本长度不会超过usize::MAX，不会溢出。且arxiv文本格式固定，所有索引由find获得，不会出现在utf-8字符中间切片的情况"
)]
#[pyfunction]
pub fn web_utils_arxiv_crawler_extract_article(html: &str) -> &str {
    let Some(start) = html.find("<article") else {
        return "";
    };
    let body_start = match html[start..].find('>') {
        Some(pos) => start + pos + 2,
        None => return "",
    };
    html[body_start..]
        .rfind("</article>")
        .map_or("", |end| &html[body_start..body_start + end - 1])
}

/// 清洗markdonify解析内容中的超链接和连续空行
///
/// # 示例
/// ```
/// web_utils_arxiv_crawler_process_markdown("引用[13](example.com/13)\n\n\n");
/// ```
///
/// # 参数
/// * `markdown_content`: markdown内容
///
/// # 返回值
/// 清理后的markdown内容
#[pyfunction]
pub fn web_utils_arxiv_crawler_process_markdown(markdown_content: &str) -> String {
    COMBINED_REGEX
        .replace_all(markdown_content, |caps: &regex::Captures| {
            caps.get(1).map_or_else(
                || "\n\n".to_owned(),
                |link_text| format!("[{}]", link_text.as_str()),
            )
        })
        .trim()
        .into()
}
