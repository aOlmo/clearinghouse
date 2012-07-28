/*
	JQuery to enable various interactions in profile.html
	Author: Gaetano Pressimone
	Last Modified: July 27, 2012
*/

/*
	make sure the page is ready before using
*/
$(document).ready(onclick_edit);
/*
When the edit button is pushed, the cell's hidden content is revealed and hides all other cells content (if previously revealed)
*/
function onclick_edit(){	
	$("button.edit").click(function(){
		if ($(this).text()=='Edit'){
			$("#middle").find("button.edit")
				.text('Edit')
				.siblings('span').hide()
				.siblings('span.value').show();
			$(this).siblings('span').show().siblings('span.value').hide();
		$(this).text('Cancel');	   
		} else {
			$(this).siblings('span').hide().siblings('span.value').show();
			$(this).text('Edit');
		}
	});
}
