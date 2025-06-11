//! `调用pandoc与typst完成格式转换`
//!
//! # Examples
//! ```rust
//! use crate::file_utils::file_conversion;
//! file_conversion::pandoc_to_markdown("file", "path/to/file.pdf", "convert/to");
//! file_utils::markdown_to_everything("path/to/file.md","convert/to","pdf");
//! ```
use pyo3::prelude::*;
use regex::Regex;
use std::ffi::OsStr;
use std::fs;
use std::io::Write as _;
use std::path::Path;
use std::process;
use std::process::{Command, Stdio};
use std::sync::LazyLock;

/// 匹配typst引用
///
/// 用于去除typst不能处理的引用
///
/// # 示例
/// ```
/// REMOVE_CITATION_PATTERN.replace_all(typst_source, "");
/// ```
pub static REMOVE_CITATION_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#cite\([^)]*\)").unwrap_or_else(|_| {
        process::exit(1);
    })
});

/// 匹配markdown图片
///
/// 用于去除pandoc/typst不能处理的图片
///
/// # 示例
/// ```
/// IMAGE_PATTERN.replace_all(markdown, "");
/// ```
pub static IMAGE_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?m)^!\[\]\([^)]+\)\{[^}]*\}").unwrap_or_else(|_| {
        process::exit(1);
    })
});

/// 用pandoc转换为markdown
///
/// # 示例
/// ```
/// pandoc_to_markdown("file", "path/to/file.pdf", "convert/to");
/// ```
///
/// # 参数
/// * `file_name`: 文件名，用于指定生成文件名。需要有后缀
/// * `original_file_path`: 文件路径
/// * `target_path`: 目标路径
#[pyfunction]
pub fn pandoc_to_markdown(file_name: &str, original_file_path: &str, target_path: &str) {
    let output_path = Path::new(target_path).join(file_name).with_extension("md");

    let Ok(output) = Command::new("pandoc")
        .args([
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-t",
            "markdown",
            original_file_path,
        ])
        .output()
    else {
        return;
    };

    if !output.status.success() {
        return;
    }

    let Ok(result) = String::from_utf8(output.stdout) else {
        return;
    };
    let cleaned_result = IMAGE_PATTERN.replace_all(&result, "");
    if fs::write(output_path, cleaned_result.as_bytes()).is_err() {}
}

/// 用pandoc转换文件
///
/// # 示例
/// ```
/// pandoc_convert(OsStr::new("file"), "path/to/file.md", Path::new("convert/to"), "docx");
/// ```
///
/// # 参数
/// * `file_name`: 文件名，不含根目录路径
/// * `original_file_path`: 完整文件路径
/// * `target_path`: 目标路径
/// * `target_ext`: 目标文件后缀
fn pandoc_convert(
    file_name: &OsStr,
    original_file_path: &str,
    target_path: &Path,
    target_ext: &str,
) {
    let output_path = Path::new(target_path)
        .join(file_name)
        .with_extension(target_ext);
    let Some(output_path_str) = output_path.to_str() else {
        return;
    };

    let Ok(mut child) = Command::new("pandoc")
        .args([
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-o",
            output_path_str,
            original_file_path,
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
    else {
        return;
    };

    if child.wait().is_err() {}
}

/// 将markdown转换为pdf
///
/// 采用pandoc转换为typst源文件，正则表达式清洗，由typst编译为pdf
///
/// # 示例
/// ```
/// markdown_to_pdf(OsStr::new("file"), "path/to/file.md", Path::new("convert/to"));
/// ```
///
/// # 参数
/// * `file_name`: 文件名，不含根目录路径
/// * `original_path`: 完整文件路径
/// * `target_path`: 目标路径
#[expect(
    clippy::arithmetic_side_effects,
    reason = "输出长度不会超过usize::MAX，且索引由find获得，不会溢出"
)]
fn markdown_to_pdf(file_name: &OsStr, original_path: &str, target_path: &Path) {
    // 执行pandoc并获取输出
    let Ok(pandoc_output) = Command::new("pandoc")
        .args([
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-t",
            "typst",
            original_path,
        ])
        .output()
    else {
        return;
    };

    if !pandoc_output.status.success() {
        return;
    }

    // 处理内容
    let Ok(mut content) = String::from_utf8(pandoc_output.stdout) else {
        return;
    };

    // 正则处理
    content = REMOVE_CITATION_PATTERN
        .replace_all(&content, "")
        .into_owned();

    // 字体替换
    if let Some(pos) = content.find("font: ()") {
        content.replace_range(
            pos..pos + 8,
            r#"font: ((name: "libertinus serif", covers: "latin-in-cjk"),"Noto Sans CJK SC")"#,
        );
    }

    // 构建pdf路径，执行typst命令
    let target_file_path = target_path.join(file_name).with_extension("pdf");
    let Some(target_file_path_str) = target_file_path.to_str() else {
        return;
    };
    let Ok(mut cmd) = Command::new("typst")
        .args(["compile", "-", target_file_path_str])
        .stdin(Stdio::piped())
        .spawn()
    else {
        return;
    };

    // 写入处理后的内容
    if let Some(mut stdin) = cmd.stdin.take() {
        if stdin.write_all(content.as_bytes()).is_err() {
            return;
        }
    }

    if cmd.wait().is_err() {}
}

/// 将markdown文件转换为其他格式
///
/// pdf使用typst编译，其他格式使用pandoc转换
///
/// # 示例
/// ```
/// markdown_to_everything("path/to/file.md","convert/to","pdf");
/// ```
///
/// # 参数
/// * `original_path`: 原始文件路径
/// * `target_path`: 目标路径
/// * `target_ext`: 目标文件后缀
#[pyfunction]
pub fn markdown_to_everything(original_path: &str, target_path: &str, target_ext: &str) {
    let trimmed_path = original_path.trim_start_matches(['/', ' ']);
    let Some(file_name) = Path::new(trimmed_path).file_name() else {
        return;
    };
    let target_path_parsed = Path::new(target_path);

    if target_ext == "pdf" {
        markdown_to_pdf(file_name, trimmed_path, target_path_parsed);
    } else {
        pandoc_convert(file_name, trimmed_path, target_path_parsed, target_ext);
    }
}
