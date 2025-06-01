//! `本地图片文件base64编码并整理为openai多模态请求格式`

use base64::{engine::general_purpose::STANDARD, Engine as _};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::LazyLock;

/// 将所有多模态模型接受的图片映射到其mime type
///
/// jpg, jpeg -> jpeg, png->png
///
/// # 示例
/// ```
/// VALID_EXTS.get(ext);
/// ```
pub static VALID_EXTS: LazyLock<HashMap<&'static str, &'static str>> = LazyLock::new(|| {
    let mut map = HashMap::new();
    map.insert("jpg", "jpeg");
    map.insert("jpeg", "jpeg");
    map.insert("png", "png");
    map
});

/// Base64编码图像文件
///
/// # 示例
/// ```
/// encode_image("media/filename.png");
/// ```
///
/// # 参数
/// * `image_path`: 图像文件路径
///
/// # 返回值
/// Base64编码的图像。若文件不存在，返回空字符串
fn encode_image(image_path: &str) -> String {
    fs::read(image_path)
        .map(|buffer| STANDARD.encode(&buffer))
        .unwrap_or_default()
}

/// 创建多模态信息
///
/// # 参数
/// * `py`: Python接口
/// * `image_path`: 图像文件路径
///
/// # 返回值
/// python字典：多模态信息，若发生任何错误，返回空字典
#[pyfunction]
pub fn create_image_component(py: Python, image_path: &str) -> Py<PyDict> {
    let dict = PyDict::new(py);
    let trimmed_path = image_path.trim_start_matches('/');
    let Some(ext) = Path::new(trimmed_path)
        .extension()
        .and_then(|ext| ext.to_str())
    else {
        return dict.into();
    };

    let Some(mime_type) = VALID_EXTS.get(ext) else {
        return dict.into();
    };

    let encoded = encode_image(trimmed_path);
    if encoded.is_empty() {
        return dict.into();
    }

    let image_url = PyDict::new(py);
    if image_url
        .set_item("url", format!("data:image/{mime_type};base64,{encoded}"))
        .is_err()
    {
        return dict.into();
    }

    if dict.set_item("type", "image_url").is_err() {
        return PyDict::new(py).into();
    }
    if dict.set_item("image_url", image_url).is_err() {
        return PyDict::new(py).into();
    }

    dict.into()
}
