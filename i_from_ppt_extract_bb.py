# -*- coding: utf-8 -*-
################### Arguments ################################################
# https://support.microsoft.com/en-us/help/827745/how-to-change-the-export-resolution-of-a-powerpoint-slide
# 72 as Decimal
###############################################################################

import win32com.client, sys
import os
import argparse
import random

CURR_LANG = ""
BATCH = 100
THRESH_HOLD_GP = 50
images_folder = ""
data_folder = os.path.join(os.getcwd(), 'data')

def charwise_hex_string(item):
    final = ''
    first_time = True
    for elem in range(len(item)):
        dec_value = ord(item[elem])
        hex_value = hex(dec_value)
        hex_value = hex_value[2:]  #0xff
        if len(hex_value) < 4:
            hex_value = '0'*(4 - len(hex_value)) + hex_value
        hex_value = 'u' + hex_value
        if first_time:
            final = hex_value
            first_time = False
        else:
            final = final + '_' + hex_value
    split_final = final.split('_u0020_')
    split_final = ' u0020 '.join(split_final)

    return split_final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("language", help="lang_ja,lang_ko,lang_es")
    args = parser.parse_args()
    global CURR_LANG
    CURR_LANG = args.language
    lang_folder, images_folder, image_pool_folder, ppt_folder = init_folder_hierarchy(data_folder, CURR_LANG)

    BATCH_COUNTER = -1

    transcription = None
    folder_for_ppt = ppt_folder
    con_set = populate_links_have(lang_folder)

    # takes care of the condition when the process and stopped. Essential since MS-PPT crashes sometimes.
    is_first_call = True

    for each_ppt in os.listdir(folder_for_ppt):
            
        if  (each_ppt.endswith('ppt') or each_ppt.endswith('pptx')):

            # launching the Microsift powerpoint
            Application = win32com.client.Dispatch("PowerPoint.Application")
            Application.Visible = True
            # ------------------------------------
            print('PPTS processed = ', len(con_set))

            if(each_ppt in con_set):
                print('continuing - ',each_ppt)
                continue  

            
            # implement the batching to save intermediate results
            
            
            if len(con_set) % BATCH == 0 or is_first_call:
                is_first_call = False
                if transcription:
                    transcription.close()

                BATCH_COUNTER  = int(len(con_set) / BATCH)

                filename = os.path.join(lang_folder, 'transcription_'+str(BATCH_COUNTER)+'.txt')
                try:
                    transcription = open(filename, 'a')
                except IOError:
                    transcription = open(filename, 'w')

                
                print('con set length = ',len(con_set), 'batch counter = ',BATCH_COUNTER)
                print("file to be used = ",filename)
            
            # ---------------------------------------------------------------
           
            # create an object for the powerpoint file
            try:
                presentation_object = Application.Presentations.Open(os.path.join(folder_for_ppt, each_ppt))
            except Exception as e:
                # corrupt slide
                print(each_ppt, 'could not open ',e)
                continue

            print("working for = ",each_ppt)
            # ppt_count += 1
            con_set.add(each_ppt)
            # open up a section in transcription for the current slide
            trans = ["SlideName - " + each_ppt]
            transcription.write(trans[0] + '\n')
            #----------------------------------------------------------

            for sl_index, each_slide_object in enumerate(presentation_object.Slides):

                print('============================ slide no ================================ ppt - ',len(con_set),'slide = ',str(sl_index+1),'/', len(presentation_object.Slides))
                
                # Divide the groups of all the slides.
                print('BEFORE number of shapes in the current slide = ', len(each_slide_object.Shapes))
                in_group_limit_satisfied = ungroup_all_shapes(each_slide_object , each_slide_object.Shapes, (THRESH_HOLD_GP))
                print('REVISED number of shapes in the current slide = ', len(each_slide_object.Shapes))
                
                if(not in_group_limit_satisfied):
                    print("skipping this slide.")
                    continue
                # -----------------------------------------
                
                # initilizaions for the slide processing.
                trans = []
                trans.append("Slide " + str(sl_index))
                was_anything_found = False
                to_be_processed_shapes = []

                print('starting to work on the shapes')
                # finally process the slide. Extract the text that is in the slides.
                for i in range(len(each_slide_object.Shapes)):
                    each_shape = each_slide_object.Shapes[i]
                    if each_shape.HasTextFrame and each_shape.TextFrame.HasText and not each_shape.HasSmartArt:
                        elems = each_shape.TextFrame.TextRange.Lines()
                        was_anything_found = save_results_for(elems, trans)
                    else: # if has text loop
                        to_be_processed_shapes.append(each_shape)
                else: # for loop else.
                    # Everything good store the slide as image
                    name = each_ppt +"_"+ str(sl_index) + "_" + str(BATCH_COUNTER) + '.jpg'
                    if was_anything_found:
                        try:
                            process_these_shapes(to_be_processed_shapes, each_slide_object, image_pool_folder)
                        except:
                            print('exception during delete shape')
                        print('saving ======= ', name)
                        each_slide_object.export(os.path.join(images_folder, name), 'JPG')
                        transcription.write('\n'.join(trans) + '\n')
            try:
                presentation_object.Close()
            except Exception as e:
                print('problem with closing the file',e)

    Application.Quit()
    transcription.close()

def save_results_for(elems, trans):
    was_anything_found = False
    for elem in elems:
        if elem.Text not in ("\r", "\n", " ", u"\u000D", u"\u000A"): # , u"\u000B", u"\u0009"
            # skip if only spaces are there
            if(elem.Text.isspace()):
                continue
            # makes it eligible for the slide to be recorded as a sample
            was_anything_found = True
            text_in_unicode = charwise_hex_string(elem.Text)
            # See the code in the end if you are trying to extract.
            trans.append(str(int(elem.BoundLeft)) + ' ' + str(int(elem.BoundTop)) + ' ' 
            + str(int(elem.BoundWidth)) + ' ' + str(int(elem.BoundHeight)) + ' ' + text_in_unicode)
    return was_anything_found

def init_folder_hierarchy(data_folder, CURR_LANG):
    lang_folder = os.path.join(data_folder, CURR_LANG)
    images_folder = os.path.join(lang_folder, 'images') # data/lang_ja/images
    image_pool_folder = os.path.join(data_folder, 'image_pool_2')
    ppt_folder = os.path.join(lang_folder, 'ppts') # ppts change
    create_directory(images_folder)
    return lang_folder, images_folder, image_pool_folder, ppt_folder


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def ungroup_all_shapes(each_slide_object, shapes, cut_off):
    print('ungrouping now')
    previous_shapes = len(each_slide_object.Shapes)
    if previous_shapes > 50:
        print('ungrouping prev cutt off')
        return False
    for each_shape in shapes:
        try:
            each_shape.Ungroup()
        except:
            # already one single and not a group.
            pass
        current_len = len(each_slide_object.Shapes)
        if current_len > cut_off:
            print('ungrouping cut- off')
            return False
    print('ungrouping complete')
    return True

def populate_links_have(lang_folder):
    _set = set()
    for each_file in os.listdir(lang_folder):
        if'transcription_' in each_file:
            filename = os.path.join(lang_folder, each_file)
            lnk_file = open(filename, 'r')
            present_lines = lnk_file.readlines()
            for each_line in present_lines:
                curr_entry = each_line.rstrip()
                if "SlideName" in curr_entry :
                    split_data = curr_entry.split(" ")[2]
                    _set.add(split_data)
            lnk_file.close()
    return _set

import time
def process_these_shapes(to_be_processed_shapes, each_slide_object, image_pool_folder):
    print('processing shapes, replacing images and deleting the rest')
    st_time = time.time()
    images_placed_set = set()
    for each_shape in to_be_processed_shapes:

        if(each_shape.Width < 10 or each_shape.Height < 10):
            delete_this_shape(each_shape)
            continue
            
        if((each_shape.Left, each_shape.Top, each_shape.Width, each_shape.Height) not in images_placed_set):
            ran_image = random.choice(os.listdir(image_pool_folder))
            sh_obj = each_slide_object.Shapes.AddPicture(os.path.join(image_pool_folder, ran_image), True, False, # change 
                                            each_shape.Left, each_shape.Top, each_shape.Width, each_shape.Height)
            while sh_obj.ZOrderPosition > 1:
                sh_obj.ZOrder(3)

            images_placed_set.add((each_shape.Left, each_shape.Top, each_shape.Width, each_shape.Height))
        
        # the shape itself is delected after the images has already been added to the to their positions.
        delete_this_shape(each_shape)
    
    print('Done processing shapes = ', time.time() - st_time)


def delete_this_shape(temp):
    try:
        temp.Delete() 
    except:
        print('exception during delete shape')

if __name__=='__main__':
    main()