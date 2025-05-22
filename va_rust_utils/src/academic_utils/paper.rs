use pyo3::prelude::*;
use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

const MIN_CHARACTER_THRESHOLD: usize = 63;

pub static SUFFIX_MAP: std::sync::LazyLock<std::collections::HashMap<&str, &str>> =
    std::sync::LazyLock::new(|| {
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

pub static LINEBREAK_RE: std::sync::LazyLock<Regex> =
    std::sync::LazyLock::new(|| Regex::new(r"\s*\n+\s*").unwrap());

/*
附加文件内容

在knowledgeBase和code目录下查找文件。代码文件放入对应代码框中。由于参数是由Gradio端根据文件列表生成的，不应出现文件不存在的情况

Parameters
----------
file: &str
    文件名
current_user_directory: &str
    当前用户根目录

Returns
----------
String
    文件内容。若为代码则放入代码框
*/
#[pyfunction]
pub fn academic_utils_paper_attach(file: &str, current_user_directory: &str) -> String {
    // 构建知识库文件路径
    let base_path = PathBuf::from("documents");
    let kb_path = base_path
        .join(current_user_directory)
        .join("knowledgeBase")
        .join(Path::new(file).with_extension("md"));

    // 优先检查知识库文件
    if let Ok(content) = fs::read_to_string(&kb_path) {
        return content;
    }

    // 构建代码文件路径
    let code_path = base_path
        .join(current_user_directory)
        .join("code")
        .join(file);

    // 检查并读取代码文件
    if let Ok(code) = fs::read_to_string(&code_path) {
        let lang = Path::new(file)
            .extension()
            .and_then(|ext| ext.to_str())
            .and_then(|ext| SUFFIX_MAP.get(ext))
            .copied()
            .unwrap_or("");

        return format!("```{lang}\n{code}\n```");
    }
    String::new()
}

/*
分段

按换行符分段，确保每段长度大于63个字符

Parameters
----------
file: &str
    文件名
current_user_directory: &str
    当前用户根目录

Returns
----------
final_list: Vec<String>
    分段后的文本
*/
#[pyfunction]
pub fn academic_utils_paper_chunk(file: &str, current_user_directory: &str) -> Vec<String> {
    let content = academic_utils_paper_attach(file, current_user_directory);
    let mut final_list = Vec::new();
    let mut temp_string = String::with_capacity(MIN_CHARACTER_THRESHOLD * 2);
    let mut char_count = 0;

    for para in LINEBREAK_RE.split(&content) {
        let para_len = para.chars().count();
        temp_string.push_str(para);
        char_count += para_len;
        if char_count > MIN_CHARACTER_THRESHOLD {
            final_list.push(std::mem::take(&mut temp_string));
            char_count = 0;
            continue;
        }
        temp_string.push_str("\n\n");
    }

    final_list.push(temp_string);

    final_list
}
