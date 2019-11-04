from glob import glob
from time import sleep
import math
import numpy as np
import cv2
import config
import model.serial_classifier as classifier
import model.classifier_util as classifier_util
import model.dataset_util as dataset_util
import windows_util as win_util
from model.grab_img import screenshot

def get_threshold(img):
    gray = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)[1]
    opening = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, np.ones((2, 2), dtype="uint8"), iterations=1)
    #canny = cv2.Canny(thresh, cv2.MORPH_CLOSE, )
    return opening

def bbox_most_left(img, offset):
    a = np.where(img != 0)
    bbox = np.min(a[0]), np.max(a[0]), np.min(a[1]), np.min(a[1])+offset
    return bbox

def eucl_dist(p1, p2):
    return math.sqrt(2 ** (p2[0] - p1[0]) + 2 ** (p2[1] - p1[1]))

def mid_bbox(bbox):
    return (bbox[0] + (bbox[2]/2), bbox[1] + (bbox[3]/2))

def connect_contours(contours, threshold):
    result = []
    for i, c_1 in enumerate(contours):
        bbox1 = cv2.boundingRect(c_1)
        mid_p1 = mid_bbox(bbox1)
        new_contour = [c_1]
        for j, c_2 in enumerate(contours):
            if i != j:
                bbox2 = cv2.boundingRect(c_2)
                mid_p2 = mid_bbox(bbox2)
                if eucl_dist(bbox1[:4], bbox2[:2]) < threshold:
                    new_contour.append(c_2)
                elif eucl_dist(bbox1[:2], bbox2[:4]) < threshold:
                    new_contour.append(c_2)
        result.append(new_contour)
        contours.pop(i)
    return result

def largest_bounding_rect(contours):
    min_x = 9999
    min_y = 9999
    max_x = 0
    max_y = 0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if x < min_x:
            min_x = x
        if y < min_y:
            min_y = y
        if x+w > max_x:
            max_x = x+w
        if y+h > max_y:
            max_y = y+h
    return (min_x, min_y, max_x, max_y)

def get_characters():
    SW, SH = win_util.get_screen_size()
    sc = screenshot(int(SW * 0.47), int(SH * 0.54), 80, 38)
    img = cv2.cvtColor(np.array(sc), cv2.COLOR_RGB2BGR)
    thresh = get_threshold(img)
    _, contours, _ = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_L1)
    contours.sort(key=lambda c: mid_bbox(cv2.boundingRect(c)))
    mask = np.zeros(thresh.shape[:2])
    masks = []
    curr_contours = []
    sub_mask = mask.copy()
    for i, c in enumerate(contours):
        x, y, w, h = cv2.boundingRect(c)
        mid_x = x + (w/2)
        next_x = -1
        if i < len(contours) - 1:
            x2, y2, w2, h2 = cv2.boundingRect(contours[i+1])
            next_x = x2 + (w2/2)
        curr_contours.append(c)
        if next_x == -1 or abs(mid_x - next_x) > 6:
            cv2.drawContours(sub_mask, curr_contours, -1, (255, 255, 255), -1)
            x1, y1, x2, y2 = largest_bounding_rect(curr_contours)
            curr_contours = []
            cropped = sub_mask[y1:y2, x1:x2]
            masks.append(cropped)
            sub_mask = mask.copy()
    filtered_masks = []
    for mask in masks:
        if mask.shape[1] > 10:
            filtered_masks.append(mask)
    return filtered_masks

def reshape_masks(masks):
    resized_masks = []
    for mask in masks:
        reshaped = mask.reshape(mask.shape + (1,))
        padded = dataset_util.pad_image(reshaped)
        resized = dataset_util.resize_img(padded, config.SERIAL_INPUT_DIM[1:])
        repeated = np.repeat(resized.reshape(((1,) + config.SERIAL_INPUT_DIM[1:])), 3, axis=0)
        resized_masks.append(repeated)
    return np.array(resized_masks)

def format_time(prediction):
    if prediction[0] == "b":
        prediction[0] = 8
    if prediction[1] == "z":
        prediction[1] = 0
    if prediction[2] == "z":
        prediction[2] = 0
    return (str(prediction[0]), str(prediction[1])+str(prediction[2]))

def get_bomb_duration(model):
    masks = get_characters()
    masks = reshape_masks(masks)
    prediction = classifier.predict(model, masks)
    best_pred = classifier_util.get_best_prediction(prediction)
    return format_time([classifier.LABELS[p] for p in best_pred])

def sleep_until_start():
    while True:
        if win_util.s_pressed():
            break
        sleep(0.1)

if __name__ == '__main__':
    sleep_until_start()
    cv2.namedWindow("Test")
    masks = get_characters()
    PATH = "../resources/training_images/timer/"
    INDEX = len(glob(PATH+"*.png"))
    for mask in masks:
        #cv2.imshow("Test", mask)
        #key = cv2.waitKey(0)
        #if key == ord('q'):
        #    break
        cv2.imwrite(f"{PATH}{INDEX:03d}.png", mask)
        print("Saved timer image.")
        INDEX += 1
