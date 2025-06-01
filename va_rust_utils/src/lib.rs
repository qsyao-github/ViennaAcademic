//! `ViennaAcademic python后端的rust扩展`
//!
//! `对academic_utils, chat_utils, file_utils, web_utils中的字符串操作/正则表达式/子进程管理等部分用Rust进行重写`
#![expect(
    clippy::single_call_fn,
    clippy::implicit_return,
    clippy::question_mark_used,
    clippy::mod_module_files,
    reason = "PyO3函数需函数签名，且必然需要?传播错误。implicit_return, mod_module_files与其余lint冲突"
)]
mod academic_utils;
mod chat_utils;
mod file_utils;
mod web_utils;
use crate::academic_utils::paper;
use crate::chat_utils::{attachment_processor, media_handler /*tool_formatter*/};
use crate::file_utils::file_conversion;
use crate::web_utils::arxiv_crawler;
use pyo3::prelude::*;

/// 预热全局变量
///
/// # 示例
/// ```
/// initialize_static();
/// ```
#[pyfunction]
fn initialize_static() {
    paper::LINEBREAK_RE.split("Line1  \n\n  Line2");
    paper::SUFFIX_MAP.get("py");
    // tool_formatter::TOOL_CALL_PATTERN.replace_all(r#"{ \n "tool_name": \n "arg_name""#, "");
    media_handler::VALID_EXTS.contains_key(&"png");
    file_conversion::REMOVE_CITATION_PATTERN.replace_all("#cite(some text)", "");
    file_conversion::IMAGE_PATTERN.replace_all(
        r#"![](media/image1.png){width="6.718607830271216in"
height="3.8802088801399823in"}"#,
        "",
    );
    arxiv_crawler::process_markdown("[[13](some_link)]\n\n\n");
}

/// 打包成Python模块
#[pymodule]
fn va_rust_utils(main_module: &Bound<'_, PyModule>) -> PyResult<()> {
    main_module.add_function(wrap_pyfunction!(initialize_static, main_module)?)?;
    main_module.add_function(wrap_pyfunction!(paper::attach, main_module)?)?;
    main_module.add_function(wrap_pyfunction!(paper::chunk, main_module)?)?;
    main_module.add_function(wrap_pyfunction!(
        attachment_processor::process_attachments,
        main_module
    )?)?;
    main_module.add_function(wrap_pyfunction!(
        media_handler::create_image_component,
        main_module
    )?)?;
    /* main_module.add_function(wrap_pyfunction!(
        tool_formatter::chat_utils_tool_formatter_format_tools,
        main_module
    )?)?; */
    main_module.add_function(wrap_pyfunction!(
        file_conversion::markdown_to_everything,
        main_module
    )?)?;
    main_module.add_function(wrap_pyfunction!(
        file_conversion::pandoc_to_markdown,
        main_module
    )?)?;
    main_module.add_function(wrap_pyfunction!(
        arxiv_crawler::extract_article,
        main_module
    )?)?;
    main_module.add_function(wrap_pyfunction!(
        arxiv_crawler::process_markdown,
        main_module
    )?)?;
    Ok(())
}
