var frames_jobs=[];  // All the info for the frames done
var select_border_size = 2; // See css **
var frames_done=[];  // Just for the frames done
var circle_radius = 20;

// Modal for selector
function addPickerModalTemplate(all_frames_ids) {
   var c; 

   if($('#select_meteor_modal').length==0) {
      c ='  <div id="select_meteor_modal" class="modal fade" tabindex="-1" style="padding-right: 0!important; width: 100vw; height: 100vh;">\
                  <div class="modal-dialog  modal-lg modal-dialog-centered box" style="width: 100vw;max-width: 100%;margin: 0; padding: 0;">\
                     <div class="modal-content" style="height: 100vh;">\
                        <div class="modal-header p-0 pt-1" style="border:none!important">\
                           <h5 class="ml-1 pt-1 mb-0">Select Meteor Position  <span id="sel_frame_id"></span></h5>\
                           <div class="alert alert-info mb-0 p-1 pr-1 pl-2">Select the <strong>POSITION</strong> on the meteor on each frame.</div>\
                           <button  class="btn btn-secondary btn-sm mr-1"  data-dismiss="modal">&times; Close</button>\
                        </div>\
                        <div id="thumb_browwser" class="d-flex flex-wrap">\
                           <div class="d-flex justify-content-left mr-2 ml-2 mb-2" id="frame_select_mod">\
                              <div id="cropped_frame_select" class="d-flex justify-content-left">\
                                 <div>\
                                 </div>\
                              </div>\
                           </div>\
                        </div>\
                        <div id="cropped_frame_selector_hoder" class="mr-3 ml-3">\
                              <div id="cropped_frame_selector" class="cur">\
                                 <div id="org_lh"></div>\
                                 <div id="org_lv"></div>\
                                 <div id="lh"></div>\
                                 <div id="lv"></div> \
                              </div>\
                        </div>\
                        <div id="below_cfs" class="d-flex justify-content-between  m-2">\
                            <div class="alert p-1 pl-1 pr-2 mb-0"><span id="fr_cnt">0</span> Frames done</div>\
                           <div class="d-flex justify-content-center text-center">\
                              <button id="skip_frame" class="btn btn-secondary btn-sm ml-3 pr-3 pl-3">Skip</button>\
                           </div>\
                           <button id="create_all" class="btn btn-primary">Create All</button>\
                        </div>\
                     </div>\
                  </div>\
               </div>';
      $(c).appendTo('body');
    } 


   // If the frames aren't on top the of the modal, we add them
   if($('#cropped_frame_select a').length == 0 ) { 
      // Get the images from the reduc table and display them in cropped_frame_select
      $.each(all_frames_ids, function(i,v) {
         
         // Get the original X and Y for the given frame (if any)
         var org_x  = $('tr#fr_' + v).attr('data-org-x');
         var org_y  = $('tr#fr_' + v).attr('data-org-y');
 
         $('<a class="select_frame select_frame_btn" data-rel="'+v+'"><span>#'+v+'  &bull; <i class="pos">x:'+org_x + ' y:'+org_y+'</i></span><img src="'+ $('#thb_'+v).find('img').attr('src') +'"></a>').appendTo($('#cropped_frame_select div'));
      });
   }  
   


   
}



// Go to Next Frame
function go_to_next(next_id) {
 
   // Does the next frame exist?
   var $next_frame = $('.select_frame[data-rel='+next_id+']');
   
   // we get the related src path

   if($next_frame.length != 0) {
      add_image_inside_meteor_select($next_frame.find('img').attr('src'), [], parseInt(next_id))
   } else {
      // We select the first one 
      var next_id = parseInt($($('#cropped_frame_select .select_frame').get(0)).attr('data-rel'));
      $next_frame = $('.select_frame[data-rel='+next_id+']');
 
      add_image_inside_meteor_select($next_frame.find('img').attr('src'),[],next_id);
   }

}



function get_neighbor_frames(cur_id) {
   // Get the thumbs & colors or -5 +5 frames
   // IN #nav_prev
   var all_thb = []; 
   cur_id = parseInt(cur_id)
   for(var i = cur_id-3; i < cur_id+4; i++) {
       var $cur_tr = $('#fr_'+i);
       var img =  $cur_tr.find('img').attr('src');
       var color = $cur_tr.find('.st').css('background-color');
       var id = i;
       vid = '';

       if(typeof img == "undefined"){
           img = './dist/img/no-sm.png';
           vid = id;
           id = '0';
       }

       if(typeof color == "undefined"){
           color = 'rgb(15,15,15)';
       } 

       all_thb.push({
           img: img,
           color:color,
           id:id,
           vid:vid
       });
   }

   return all_thb;

}


// Add Circle Repair
function addCircleRepair(x,y,fn,after_of_before) {
   var $cir = $('<div class="circl"><span>'+fn+'</span></div>');

   $cir.appendTo($('#cropped_frame_selector'));
   $cir.css({
      'left': parseInt(x-circle_radius/2) + 'px',
      'top':  parseInt(y-circle_radius/2) + 'px' 
   });

   if(after_of_before=='b') {
      $cir.css('border-color','red');
   } else {
      $cir.css('border-color','green');
   }
   
}



// Change Local x,y to Real x,y
function convert_from_local(_x,_y) {
   return [_x+x, _y+y];
}




// Add Image Inside Picker
function add_image_inside_meteor_select(img_path, all_frames_ids, meteor_id) { 


   // Remove Previous Circles
   $('.circl').remove();

   $('#cropped_frame_selector').css('background-image','url('+img_path+')');


   // Add image 
   var height = $('#select_meteor_modal').outerHeight() - $('#select_meteor_modal .modal-header').outerHeight() - $("#thumb_browwser").outerHeight() - $('#below_cfs').outerHeight();
   $('#cropped_frame_selector').css('height',height- 30)
   $('#cropped_frame_selector').css('width', parseInt(height*16/9));   
   $('#sel_frame_id, .sel_frame_id').text(' - #' +  meteor_id);   


   // Add Cur to image chooser
   $('.select_frame').removeClass('cur');
   $('.select_frame[data-rel="'+meteor_id+'"]').addClass('cur');


   // Scrolln top
   var $frame = $('.select_frame[data-rel='+meteor_id+']');
   var scroll_to = meteor_id-4;

   // Cur has changed
   $('.select_frame').removeClass('cur');
   $frame.addClass('cur');

   // Not "done" yet
   $('#cropped_frame_selector').removeClass('done');

   // We load the image
   $('#cropped_frame_selector').css({
      'background-image':'url('+$($frame.find('img')).attr('src')+')'
   }); 

   // Scroll to frame -1 on top if it exists
   if($('.select_frame[data-rel="'+scroll_to+'"]').length==0) {
      scroll_to-= 1;
      while($('.select_frame[data-rel="'+scroll_to+'"]').length==0 && scroll_to>=0) {
         scroll_to-= 1;
      }
   }
   $('#frame_select_mod').scrollTo($('.select_frame[data-rel="'+scroll_to+'"]'), 150 );


   // Add circles for 3 frames before and 3 frames after
      // get the 3 frames before
      var frames_before = [];
      for(var i = meteor_id; i >= meteor_id - 3 ; i--) {  
         if($('#fr_'+meteor_id).length>0 && i!=meteor_id) {
            xy = convert_from_local(parseInt($('#fr_'+i).attr('data-org-x')),$('#fr_'+i).attr('data-org-y'))
            frames_before.push({'fn':i,'org_x': xy[0],'org_y': xy[1]});
         }
      }

     // get the 3 frames afeter
     var frames_after = [];
     for(var i = meteor_id; i <= meteor_id + 3 ; i++ ) {
        if($('#fr_'+meteor_id).length>0 && i!=meteor_id) {
         real_x, real_y = convert_from_local(parseInt($('#fr_'+i).attr('data-org-x')),$('#fr_'+i).attr('data-org-y'))
         frames_after.push({'fn':i,'org_x': xy[0],'org_y': xy[1]});
      }
     }
     
   // Add Circles Before 
   $.each(frames_before, function(i,v) { 
      addCircleRepair(v['org_x'],v['org_y'],v['fn'],'b');
   });

   $.each(frames_after, function(i,v) { 
      addCircleRepair(v['org_x'],v['org_y'],v['fn'],'a');
   });



   // Select Meteor
   $("#cropped_frame_selector").unbind('click').click(function(e){
     
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;

      var factor  = w / $('#cropped_frame_selector').width();  // Same for W & H!!
 
      // Convert into HD_x & HD_y
      // from x,y
      var realX = relX*factor+x;
      var realY = relY*factor+y;
 
      // Transform values
      if(!$(this).hasClass('done')) {
          $(this).addClass('done');
      } else {
          $('#lh').css('top',relY);
          $('#lv').css('left',relX); 
      }
 
      cur_fr_id = $('#cropped_frame_select .cur').attr('data-rel');

      // Add current frame to frame_done if not already there
      if($.inArray(cur_fr_id, frames_done )==-1) {
         frames_done.push(parseInt(cur_fr_id));  // We push an int so we can get the min
         $('#fr_cnt').html(parseInt($('#fr_cnt').html())+1);
      }

      // Add info to frames_jobs
      frames_jobs.push({
         'fn': cur_fr_id,
         'x': realX,
         'y': realY,
         'pos_x': relX,
         'pos_y': relY
      });
      
      // Add info to frame scroller
      $('#cropped_frame_select .cur').addClass('done').find('.pos').html('<br>x:' + parseInt(realX) + ' y:'  + parseInt(realY));
      
      // Go to next frame
      go_to_next(parseInt(cur_fr_id)+1);
      
  }).unbind('mousemove').mousemove(function(e) {
      
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;

      // Cross
      if(!$(this).hasClass('done')) {
          $('#lh').css('top',relY-2);
          $('#lv').css('left',relX-2); 
      }
       
  });

   /*
   // If we already have data: we show the circle
   // and the reset button
   var cur_f_done = false;
   $.each(frames_jobs, function(i,v){
      if(typeof v !=='undefined' && v['fn']==fd_id) {
          // Warning -5 because the circle has a 10px diameter 
         $('#cirl').css({
            'left': parseInt(v['pos_x']-5) + 'px',
            'top':  parseInt(v['pos_y']-5) + 'px' 
         }).show();
         
         $('#reset_frame').css('visibility','visible');
         cur_f_done = true;
      }
   });


   if(!cur_f_done){
      $('#cirl').hide();
      $('#reset_frame').css('visibility','hidden');
   }
   */
   return false;
 
}


// Update Modal Template
// MAke one frame active
function updateModalTemplate(meteor_id,img_path,all_frames_ids) {
 

   // Show Modal if necessary
   if($('#select_meteor_modal').hasClass('show')) { 
      add_image_inside_meteor_select(img_path, all_frames_ids,meteor_id);
      $('#select_meteor_modal').css('padding-right',0);
      $('body').css('padding',0);
   } else {
      // When the modal already exists 
      
      $('#select_meteor_modal').on('shown.bs.modal', function () {
         add_image_inside_meteor_select(img_path, all_frames_ids,meteor_id);
         $('#select_meteor_modal').css('padding-right',0);
         $('body').css('padding',0); // Because we don't want slidebars on body
      }).modal('show');
   }  


   $('.select_frame').unbind('click').click(function() {
      var $t = $(this);
      var MID = $t.attr('data-rel');
      var img_path = $('#thb_' + MID + " img").attr('src');
      $('#cropped_frame_selector').css('background-image','url(none)').css('border','2px solid #ffe52e');
      add_image_inside_meteor_select(img_path,all_frames_ids,MID)
   });

}


// Open the Modal with a given meteor
function open_meteor_picker(meteor_id, img_path,all_frames_ids ) {
   updateModalTemplate(meteor_id,img_path,all_frames_ids);
   return false; 
} 



/*******************************
 * MAIN SETUP
 **/

function setup_manual_reduc1() { 
   var all_frames_ids = [];

   // Only for loggedin
   if(test_logged_in()==null) {
      return false;
   }

   // Get all the frame ids
   $('#reduc-tab table tbody tr').each(function() {
      var id = $(this).attr('id');
      id = id.split('_');
      all_frames_ids.push(parseInt(id[1]));
   });
  
   // Add modal Template 
   addPickerModalTemplate(all_frames_ids); 

   // Click on selector (thumb)
   $('.wi a').click(function(e) { 
      var $tr = $(this).closest('tr'); 

      e.stopPropagation();

      // Get meteor id
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];
 
      open_meteor_picker(meteor_id,$tr.find('img').attr('src'),all_frames_ids);


      return false;
   });


   // Click on "Big" button 
   $('.reduc1').click(function(e) { 

      // Find first id in the table
      var $tr = $('#reduc-tab table tbody tr');
       
      $tr = $($tr[0]); 
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];

      // Then Do the all thing to open the meteor picker 
      open_meteor_picker(meteor_id,$tr.find('img').attr('src'),all_frames_ids);

      return false;
   });

}