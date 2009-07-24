
$(document).ready(function() {
	toggle_upload();
	$("#id_gen_upload_choice").change(toggle_upload);
});

function toggle_upload() {
	if ($("#id_gen_upload_choice").val() == "1") {
		$("#uploadkey").hide();
	} else {
		$("#uploadkey").show();
	}
}
