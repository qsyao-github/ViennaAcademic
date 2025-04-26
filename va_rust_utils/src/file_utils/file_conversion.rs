use once_cell::sync::Lazy;
use pyo3::prelude::*;
use regex::Regex;
use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};

pub static REMOVE_CITATION_PATTERN: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"#cite\([^)]*\)").unwrap());

/*
用pandoc转换文件

Parameters
----------
file_basename: &str
    文件名，不含后缀和根目录路径
original_file_path: &str
    完整文件路径
target_path: &str
    目标路径
target_ext: &str
    目标文件后缀
*/
fn pandoc_convert(
    file_basename: &str,
    original_file_path: &str,
    target_path: &str,
    target_ext: &str,
) {
    let output_path = Path::new(target_path).join(format!("{}.{}", file_basename, target_ext));

    let _ = Command::new("pandoc")
        .args(&[
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-o",
            output_path.to_str().unwrap(),
            original_file_path,
        ])
        .output();
}

/*
将markdown转换为pdf

采用pandoc转换为typst源文件，正则表达式清洗，由typst编译为pdf

Parameters
----------
file_basename: &str
    文件名，不含后缀和根目录路径
original_path: &str
    完整文件路径
target_path: &str
    目标路径
*/
fn markdown_to_pdf(file_basename: &str, original_path: &str, target_path: &str) {
    // 执行pandoc并获取输出
    let pandoc_output = Command::new("pandoc")
        .args([
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-t",
            "typst",
            original_path,
        ])
        .output()
        .unwrap();

    if !pandoc_output.status.success() {
        eprintln!("{}", String::from_utf8_lossy(&pandoc_output.stderr));
        return;
    }

    // 处理内容
    let mut content = String::from_utf8(pandoc_output.stdout).unwrap();

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

    // 执行typst命令
    let mut cmd = Command::new("/home/laowei/typst-x86_64-unknown-linux-musl/typst")
        .args([
            "compile",
            "-",
            &format!("{}/{}.pdf", target_path, file_basename),
        ])
        .stdin(Stdio::piped())
        .spawn()
        .unwrap();

    // 写入处理后的内容
    if let Some(mut stdin) = cmd.stdin.take() {
        stdin.write_all(content.as_bytes()).unwrap();
    }
    let status = cmd.wait().unwrap();
    if !status.success() {
        eprintln!("Failed status code: {:?}", status.code());
    }
}

/*
将markdown文件转换为其他格式

pdf使用typst编译，其他格式使用pandoc转换
Parameters
----------
original_path: &str
    原始文件路径
target_path: &str
    目标路径
target_ext: &str
    目标文件后缀
*/
#[pyfunction]
pub fn file_utils_file_conversion_markdown_to_everything(
    original_path: &str,
    target_path: &str,
    target_ext: &str,
) {
    let path = Path::new(original_path);
    let file_name = path.file_stem().unwrap().to_str().unwrap();

    if target_ext != "pdf" {
        pandoc_convert(file_name, original_path, target_path, target_ext);
    } else {
        markdown_to_pdf(file_name, original_path, target_path);
    }
}
