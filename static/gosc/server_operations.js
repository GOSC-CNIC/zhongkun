;
var VM_TASK_CN = {
    'start': '启动',
    'reboot': '重启',
    'shutdown': '关闭',
    'poweroff': '关闭电源',
    'delete': '删除',
    'reset': '重置',
    'delete_force': '强制删除'
};

var VM_STATUS_CN = {
    0: '无状态', //无状态
    1: '运行',
    2: '阻塞',
    3: '暂停',
    4: '关机',
    5: '关机',
    6: '崩溃',
    7: '暂停',
    9: '宿主机连接失败',  //宿主机连接失败
    10: '丢失',  //虚拟机丢失
    11: '正在创建',
    12: '创建失败',
    13: '云主机错误'
};

var VM_STATUS_LABEL = {
        0: 'default',
        1: 'success',
        2: 'info',
        3: 'info',
        4: 'info',
        5: 'info',
        6: 'danger',
        7: 'info',
        8: 'default',
        9: 'danger',
        10: 'warning',
        11: 'secondary',
        12: 'danger',
        13: 'danger'
};

// 虚拟机detail api构建
function build_vm_detail_api(vm_uuid){
    let url = 'api/server/' + vm_uuid;
    return build_absolute_url(url);
}

// 虚拟机操作api构建
function build_vm_operations_api(vm_uuid){
    let url = 'api/server/' + vm_uuid + '/action';
    return build_absolute_url(url);
}

// 虚拟机系统快照创建api构建
function build_vm_snap_create_api(vm_uuid, remarks){
    let url = 'api/server/' + vm_uuid + '/snap' + '?remark=' + remarks;
    return build_absolute_url(url);
}

function get_err_msg_or_default(xhr, default_msg) {
    let msg = default_msg;
    try {
        let data = xhr.responseJSON;
        if (data.hasOwnProperty('message')) {
            msg = default_msg + data.message;
        }
    }catch (e) {

    }
    return msg;
}

// 启动虚拟机
function start_vm_ajax(vm_uuid, before_func, complate_func){
    let api = build_vm_operations_api(vm_uuid);
    if(typeof(before_func) === "function"){
        before_func();
    }
    $.ajax({
        url: api,
        type: 'post',
        data: {
            'action': 'start',
        },
        success: function (data, status_text) {
        },
        error: function (xhr, msg, err) {
            msg = get_err_msg_or_default(xhr, '启动虚拟机失败;');
            alert(msg);
        },
        complete:function (xhr, ts) {
            if(typeof(complate_func) === "function"){
                complate_func();
            }
        }
    });
}

// 重启虚拟机
function reboot_vm_ajax(vm_uuid, before_func, complate_func){
    let api = build_vm_operations_api(vm_uuid);
    if(typeof(before_func) === "function"){
        before_func();
    }
    $.ajax({
        url: api,
        type: 'post',
        data: {
            'action': 'reboot',
        },
        success: function (data, status_text) {
        },
        error: function (xhr, msg, err) {
            msg = get_err_msg_or_default(xhr, '重启虚拟机失败;');
            alert(msg);
        },
        complete:function (xhr, ts) {
            if(typeof(complate_func) === "function"){
                complate_func();
            }
        }
    });
}

// 关机虚拟机
function shutdown_vm_ajax(vm_uuid, before_func, complate_func){
    let api = build_vm_operations_api(vm_uuid);
    if(typeof(before_func) === "function"){
        before_func();
    }
    $.ajax({
        url: api,
        type: 'post',
        data: {
            'action': 'shutdown',
        },
        success: function (data, status_text) {
        },
        error: function (xhr, msg, err) {
            msg = get_err_msg_or_default(xhr, '虚拟机关机失败;');
            alert(msg);
        },
        complete:function (xhr, ts) {
            if(typeof(complate_func) === "function"){
                complate_func();
            }
        }
    });
}

// 强制断电虚拟机
function poweroff_vm_ajax(vm_uuid, before_func, complate_func){
    let api = build_vm_operations_api(vm_uuid);
    if(typeof(before_func) === "function"){
        before_func();
    }
    $.ajax({
        url: api,
        type: 'post',
        data: {
            'action': 'poweroff',
        },
        success: function (data, status_text) {
        },
        error: function (xhr, msg, err) {
            msg = get_err_msg_or_default(xhr, '强制断电失败;');
            alert(msg);
        },
        complete:function (xhr, ts) {
            if(typeof(complate_func) === "function"){
                complate_func();
            }
        }
    });
}

// 删除虚拟机
function delete_vm_ajax(vm_uuid, op='delete', before_func, success_func, complate_func){
    let api = build_vm_detail_api(vm_uuid);
    if (op === 'delete_force'){
        api = api + '?force=true'
    }
    if(typeof(before_func) === "function"){
        before_func();
    }
    $.ajax({
        url: api,
        type: 'delete',
        success: function (data, status_text) {
            if(typeof(success_func) === "function"){
                success_func();
            }
        },
        error: function (xhr, msg, err) {
            msg = get_err_msg_or_default(xhr, '删除虚拟机失败;');
            alert(msg);
            if(typeof(complate_func) === "function"){
                complate_func();
            }
        }
    });
}


// 创建虚拟机系统快照
function create_snap_vm_ajax(vm_uuid, remarks, before_func, success_func, complate_func){
    let api = build_vm_snap_create_api(vm_uuid, remarks);
    if(typeof(before_func) === "function"){
        before_func();
    }
    $.ajax({
        url: api,
        type: 'post',
        success: function (data, status_text) {
            if(typeof(success_func) === "function"){
                success_func(data);
            }
        },
        error: function (xhr, msg, err) {
            msg = get_err_msg_or_default(xhr, '创建主机快照失败;');
            alert(msg);
        },
        complete:function (xhr, ts) {
            if(typeof(complate_func) === "function"){
                complate_func();
            }
        }
    });
}

