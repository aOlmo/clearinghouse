$(document).ready(toggle_detail);

function toggle_detail() {
	$("#expand").click(function () {
		$("#action_detail").toggle();
		if ($(this).text() == "[+]") {
			$(this).text("[-]");
		} else {
			$(this).text("[+]");
		}
	});
}