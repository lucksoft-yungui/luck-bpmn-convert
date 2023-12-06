from flask import Flask, render_template, request, send_from_directory, jsonify
import os
import json
from lxml import etree

app = Flask(__name__)

# 获取当前app.py文件的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))
# 设置UPLOAD_FOLDER为project_root/uploads
UPLOAD_FOLDER = os.path.join(basedir, '../uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return '没有文件被上传', 400

    file = request.files['file']

    if file.filename == '':
        return '没有选择文件', 400

    if file and file.filename.endswith('.bpmn'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        processed_file_path = process_bpmn(file_path)  # 调用BPMN处理函数
        return jsonify({'filename': os.path.basename(processed_file_path)})
    return '无效的文件类型', 400

def format_xml(root):
    """
    Formats the XML file for pretty printing.
    """
    for element in root.iter():
        if len(element):  # if the element has children
            element.text = '\n' + '  ' * (element.getroottree().getpath(element).count('/') + 1)
            if not element.tail or not element.tail.strip():
                element.tail = '\n' + '  ' * element.getroottree().getpath(element).count('/')
        else:  # if it's a leaf
            if not element.tail or not element.tail.strip():
                element.tail = '\n' + '  ' * element.getroottree().getpath(element).count('/')


def process_bpmn(file_path):
    # 解析BPMN文件
    tree = etree.parse(file_path)
    root = tree.getroot()

    namespaces = {
        'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'activiti': 'http://activiti.org/bpmn'
    }

    for userTask in root.xpath('.//bpmn2:userTask', namespaces=namespaces):
        # 检查是否已经包含multiInstanceLoopCharacteristics
        if not userTask.xpath('.//bpmn2:multiInstanceLoopCharacteristics', namespaces=namespaces):
            documentation = userTask.find('{http://www.omg.org/spec/BPMN/20100524/MODEL}documentation')
            if documentation is not None:
                try:
                    
                    userTask_id = userTask.get('id')

                    # 添加或更新 activiti:assignee 属性
                    assignee_value = f"${{{'assignee_' + userTask_id}}}"
                    userTask.set('{http://activiti.org/bpmn}assignee', assignee_value)

                    # 检查并移除 activiti:collection 属性（如果存在）
                    collection_attribute = '{http://activiti.org/bpmn}candidateUsers'
                    if collection_attribute in userTask.attrib:
                        del userTask.attrib[collection_attribute]

                    doc_json = json.loads(documentation.text)
                    userGroups = doc_json.get('userGroups', [])

                    collection_value = '_u_' if all('sclassKey' not in u for u in userGroups) else '_g_'
                    collection_value += '_or_'.join(str(u.get('sgroupKey' if collection_value.startswith('_g_') else 'indocno', '')) for u in userGroups)

                    multiInstanceLoop = etree.Element('{http://www.omg.org/spec/BPMN/20100524/MODEL}multiInstanceLoopCharacteristics', {
                        'isSequential': "true",
                        '{http://activiti.org/bpmn}elementVariable': f"assignee_{userTask_id}",
                        '{http://activiti.org/bpmn}collection': collection_value
                    })
                    completionCondition = etree.SubElement(multiInstanceLoop, '{http://www.omg.org/spec/BPMN/20100524/MODEL}completionCondition')
                    completionCondition.text = '${nrOfCompletedInstances/nrOfInstances >= 0.01}'

                    userTask.append(multiInstanceLoop)

                    doc_json['rate'] = 1
                    documentation.text = json.dumps(doc_json)
                except json.JSONDecodeError:
                    pass
    # 在返回之前格式化整个XML文档
    format_xml(root)

    # 保存修改后的文件
    modified_file_path = 'modified_' + os.path.basename(file_path)
    modified_file_path = os.path.join(UPLOAD_FOLDER, modified_file_path)
    tree.write(modified_file_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return modified_file_path

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    print(filename)
    print(app.config['UPLOAD_FOLDER'])
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)