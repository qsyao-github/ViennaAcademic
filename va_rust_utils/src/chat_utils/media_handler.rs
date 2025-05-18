use base64::{engine::general_purpose::STANDARD, Engine as _};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashSet;
use std::fs::File;
use std::io::Read;
use std::path::Path;

pub static VALID_EXTS: std::sync::LazyLock<HashSet<&'static str>> =
    std::sync::LazyLock::new(|| {
        let mut set = HashSet::new();
        set.insert("jpg");
        set.insert("jpeg");
        set.insert("png");
        set
    });

/*
Base64编码图像文件

Parameters
----------
image_path: &str
    图像文件路径

Returns
----------
String
    Base64编码的图像。若文件不存在，返回空字符串
*/
fn chat_utils_media_handler_encode_image(image_path: &str) -> String {
    let mut buffer = Vec::new();
    File::open(image_path)
        .and_then(|mut f| f.read_to_end(&mut buffer))
        .map(|_| STANDARD.encode(&buffer))
        .unwrap_or_default()
}

/*
创建多模态信息

Parameters
----------
py: Python
    Python接口
image_path: &str
    图像文件路径

Returns
----------
Py<PyDict>
    python字典：多模态信息，若文件不存在，则返回空字典
*/
#[pyfunction]
pub fn chat_utils_media_handler_create_image_component(py: Python, image_path: &str) -> Py<PyDict> {
    let dict = PyDict::new(py);

    let Some(ext) = Path::new(&image_path).extension().and_then(|e| e.to_str()) else {
        return dict.into();
    };

    if !VALID_EXTS.contains(ext) {
        return dict.into();
    }

    let encoded = chat_utils_media_handler_encode_image(image_path);
    if encoded.is_empty() {
        return dict.into();
    }

    let image_url = PyDict::new(py);
    image_url
        .set_item("url", format!("data:image/{ext};base64,{encoded}"))
        .unwrap();

    dict.set_item("type", "image_url").unwrap();
    dict.set_item("image_url", image_url).unwrap();

    dict.into()
}
