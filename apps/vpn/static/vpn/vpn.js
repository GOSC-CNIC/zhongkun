;(function () {

    //API域名
    let DOMAIN_NAME = get_domain_url();

    // 获取API域名
    function get_api_domain_name(){
        return DOMAIN_NAME;
    }

    // 构建带域名url
    function build_url_with_domain_name(url){
        let domain = get_api_domain_name();
        domain = domain.rightStrip('/');
        if(!url.startsWith('/'))
            url = '/' + url;
        return domain + url;
    }

        //
    //所有ajax的请求的全局设置
    //
    $.ajaxSettings.beforeSend = function(xhr, settings){
        var csrftoken = getCookie('csrftoken');
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    };

    $(".vpn-password").on("dblclick", function (e) {
        e.preventDefault();
        let serviceId = $(this).attr('data-service-id');
        let remarks = $(this).children('.vpn-password-value');
        let old_html = remarks.text();
        old_html = old_html.replace(/(^\s*) | (\s*$)/g,'');

        //如果已经双击过，正在编辑中
        if(remarks.attr('data-in-edit') === 'true'){
            return;
        }
        // 标记正在编辑中
        remarks.attr('data-in-edit', 'true');
        //创建新的input元素，初始内容为原备注信息
        var newobj = document.createElement('input');
        newobj.type = 'text';
        newobj.value = old_html;
        //设置该标签的子节点为空
        remarks.empty();
        remarks.append(newobj);
        newobj.setSelectionRange(0, old_html.length);
        //设置获得光标
        newobj.focus();
        //为新增元素添加光标离开事件
        newobj.onblur = function () {
            remarks.attr('data-in-edit', '');
            remarks.empty();
            let input_text = this.value;
            // 如果输入内容修改了
            if (input_text && (input_text !== old_html)){
                if (input_text.length < 6){
                    remarks.append(old_html);
                    alert('密码长度不得小于6个字符');
                    return;
                }
                // 请求修改ftp密码
                let url = build_url_with_domain_name('api/vpn/' + serviceId + '/');
                $.ajax({
                    url: url,
                    type: "PATCH",
                    data: {password: input_text},
                    content_type: "application/json",
                    timeout: 5000,
                    async: false,
                    success: function (res, statusText, xhr) {
                        if(xhr.status === 200){
                            remarks.append(input_text);
                            alert("修改密码成功");
                        }
                    },
                    error: function(xhr, statusText){
                        let msg = '请求失败';
                        if (statusText === 'timeout') {// 判断超时后 执行
                            msg = "请求超时";
                        }else if (xhr.responseJSON.hasOwnProperty('message')){
                            msg = xhr.responseJSON.message;
                        }
                        remarks.append(old_html);
                        alert('修改密码失败,' + msg);
                    },
                    headers: {'X-Requested-With': 'XMLHttpRequest'},//django判断是否是异步请求时需要此响应头
                });
            }else{
                remarks.append(old_html);
            }
        };
    });
})();