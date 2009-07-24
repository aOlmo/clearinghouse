$(document).ready(function() {
	detectOs();
});

function detectOs() {
	var os = $.browser.OS();
	switch (os) {
		case "Windows":
			$("#downloads").prepend($("#win"));
			break;
		case "Mac":
			$("#downloads").prepend($("#mac"));
			break;
		case "Linux":
			$("#downloads").prepend($("#linux"));
			break;
		default:
			break;
	}
}
