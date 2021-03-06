
// UI - greyout a detection that we send to the API
function greyOut($el,msg) {
   $el.addClass('done');
   $el.find('.btn-toolbar').remove();

}



function send_API_frame_task(frameData,callback) {
   var usr = getUserInfo();
   var frame_data_to_send = [];
   usr = usr.split('|');
   $('body').addClass('wait');
    

   // Get current detection 
   var video_API_path = cropped_video.replace(/^.*[\\\/]/, '');
   video_API_path = video_API_path.replace('-prev-crop.jpg','');
   video_API_path = video_API_path.replace('-HD-cropped.mp4','');

   // To limit the banwidth we're sending an array [fn,x,y] to the API
   // instead of a JSON  
   $.each(frameData,function(i,v) {
      frame_data_to_send.push([v['fn'],v['x'],v['y']])
   });
   
   console.log("FRAME DATA TO SEND ");
   console.log(frame_data_to_send.toString());


   $.ajax({ 
      url:   API_URL ,
      data: {'function':'update_frames',  'tok':test_logged_in(), 'data': frame_data_to_send.toString(), 'file':video_API_path, 'usr':usr[0], 'st':stID}, 
      format: 'json', 
      success: function(data) { 
         $('body').removeClass('wait');
         data = jQuery.parseJSON(data); 

         if(typeof data.error !== 'undefined') {

            // WRONG!
            bootbox.alert({
               message: data.error,
               className: 'rubberBand animated error',
               centerVertical: true 
            });

            // Login out if it's a login error
            if(typeof data.log !== 'undefined' && data.log==1) {
               logout();
               loggedin();
            }

         }  else {

             
            bootbox.alert({
               message: data.msg,
               className: 'rubberBand animated',
               centerVertical: true,
               backdrop: true
            }); 

            // We add a cookie so we know the page has been updated
            createCookie(PAGE_MODIFIED,window.location.href,1/24);
          
         } 
       
         callback();

         return true;
           
      }, 
      error:function() { 
         
         $('body').removeClass('wait');

         bootbox.alert({
            message: "Impossible to reach the API. Please, try again later or refresh the page and log back in",
            className: 'rubberBand animated error',
            centerVertical: true 
         });
         
         callback();
         return false;
      }
   }); 

}


function send_API_task(jsonData,$toDel,$toConf,callback) {
 
   var usr = getUserInfo();
   usr = usr.split('|');

   $('body').addClass('wait');

   $.ajax({ 
      url:   API_URL ,
      data: {'function':'tasks',  'tok':test_logged_in(), 'data': jsonData, 'usr':usr[0], 'st':stID}, 
      format: 'json', 
      success: function(data) { 
         $('body').removeClass('wait');
         data = jQuery.parseJSON(data); 

         if(typeof data.error !== 'undefined') {

            // WRONG!
            bootbox.alert({
               message: data.error,
               className: 'rubberBand animated error',
               centerVertical: true 
            });

            // Login out if it's a login error
            if(typeof data.log !== 'undefined' && data.log==1) {
               logout();
               loggedin();
            }

         }  else {

            // We grey out the related detections on the page
            if($toDel.length>0) {
               $.each($toDel, function(i,v) {
                  greyOut(v,'del');
               })
            }

            // We grey out the related detections on the page
            if($toConf.length>0) {
               $.each($toConf, function(i,v) {
                  greyOut(v,'conf');
               })
            }

            // Update main button
            $('#del_text').text('');
            $('#conf_text').text('');
 
            bootbox.alert({
               message: data.msg,
               className: 'rubberBand animated',
               centerVertical: true,
               backdrop: true
            });
            
 

            // We add a cookie so we know the page has been updated
            createCookie(PAGE_MODIFIED,window.location.href,1/24);
            already_done();
         }
 
       
         callback();

         return true;
           
      }, 
      error:function() { 
         
         $('body').removeClass('wait');

         bootbox.alert({
            message: "Impossible to reach the API. Please, try again later or refresh the page and log back in",
            className: 'rubberBand animated error',
            centerVertical: true 
         });
         
         callback();
         return false;
      }
   });
}


// Big yellow button on bottom of daily report
function update_all() {

   // Send a list of task to the API
   $('#bottom_action_bar .btn').click(function() {

      var toDel = [], toConf = [], $toDel = [], $toConf = [], msg = "You are about to ", toDelB = false, toDelC = false;

      // Get All to delete
      $('.prevproc.toDel').each(function() {
         var $t = $(this);
         var path = $t.find('a.T>img').attr('src');

         // Here we get only the file name 
         // as all the should be in the filename (+ station ID that is passed to the API)
         // We also remove -prev-crop.jpg
         path = path.replace(/^.*[\\\/]/, '')
         path = path.replace('-prev-crop.jpg','');
 
         toDel.push(path);
         $toDel.push($t);
         toDelB = true;
      });

      if(toDel.length>0) {
         if(toDel.length>1) {
            t = "detections"
         } else {
            t = "detection"
         }
         msg += " <b>delete " + toDel.length + " " + t + "</b>";
      }

      // Get All to confirm
      $('.prevproc.toConf').each(function() {
         var $t = $(this);
         var path = $t.find('a.T>img').attr('src'); 
         // Here we get only the file name 
         // as all the should be in the filename (+ station ID that is passed to the API)
         // We also remove -prev-crop.jpg
         path = path.replace(/^.*[\\\/]/, '')
         path = path.replace('-prev-crop.jpg','');
         toConf.push(path);
         $toConf.push($t);
         toDelC = true;
      });

      if(toConf.length>0 ) {
         if(toConf) {
            msg += " and " ;
         }
         if(toConf.length>1) {
            t = "detections"
         } else {
            t = "detection"
         } 
         msg += " <b>confirm " + toConf.length + " " + t + "</b>";
      }

      if(toDel || toConf) {
         // Bootbox Confirm
         bootbox.confirm({
            message: msg + ".<br/>Please, confirm.",
            centerVertical: true,
            backdrop: true,
            buttons: {
               cancel: {
                  label: 'No',
                  className: 'btn-danger'
               },
               confirm: {
                  label: 'Yes',
                  className: 'btn-success'
               }
            },
            callback: function (result) {
               if(result==true) { 
                  send_API_task({'toDel':toDel.toString(),'toConf':toConf.toString()},$toDel,$toConf, function() {});
               } 
            }
         });
      } 
   })
} 


$(function() {
   // Setup big yellow button on daily report
   update_all();
})