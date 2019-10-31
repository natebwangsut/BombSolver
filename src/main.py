from time import sleep
from numpy import array, argmax
import cv2
from debug import log
from model.grab_img import screenshot, load_test_images
import windows_util as win_util
import model.classifier as classifier
import config
import model.dataset as dataset

def sleep_until_start():
    while True:
        if win_util.s_pressed():
            break
        sleep(0.1)

def start_level():
    SW, SH = win_util.get_screen_size()
    win_util.click(int(SW - SW/2.6), int(SH - SH/3.3))

def wait_for_light():
    sleep(16)

def inspect_side(mx, my, sx, sy, sw, sh):
    win_util.mouse_move(mx, my)
    sleep(0.5)
    SC = screenshot(sx, sy, sw, sh)
    sleep(0.2)
    return SC

def inspect_bomb():
    SW, SH = win_util.get_screen_size()
    mid_x = SW // 2
    mid_y = SH // 2
    win_util.click(mid_x, mid_y + (mid_y // 8))
    sleep(0.5)
    # Inspect front of bomb.
    front_img = screenshot(460, 220, 1000, 640)
    front_img.save("../front.png")
    sleep(0.2)
    # Rotate bomb.
    win_util.mouse_down(mid_x, mid_y, btn="right")
    sleep(0.2)
    # Inspect right side.
    right_img = inspect_side(SW - int(SW / 2.74), mid_y + int(mid_y / 8), 755, 60, 480, 900)
    right_img.save("../left.png")
    # Inspect left side.
    left_img = inspect_side(int(SW / 2.76), mid_y + int(mid_y / 8), 755, 60, 480, 900)
    left_img.save("../right.png")
    # Inspect top side.
    top_img = inspect_side(int(SW / 2.75), SH, 720, 0, 480, SH)
    top_img.save("../top.png")
    # Inspect bottom side.
    bottom_img = inspect_side(int(SW / 2.75), 0, 720, 0, 480, SH)
    bottom_img.save("../bot.png")
    # Inspect back of bomb.
    win_util.mouse_up(mid_x, mid_y, btn="right")
    sleep(0.5)
    win_util.click(SW - 100, 100, btn="right")
    sleep(0.5)
    win_util.click(mid_x, mid_y + (mid_y // 8))
    sleep(0.2)
    win_util.mouse_down(mid_x, mid_y, btn="right")
    sleep(0.5)
    back_img = inspect_side(SW - int(SW / 4.45), mid_y + (mid_y // 9), 460, 220, 1000, 640)
    back_img.save("../back.png")
    sleep(0.2)
    win_util.mouse_up(mid_x, mid_y, btn="right")
    return (front_img, back_img, left_img, right_img, top_img, bottom_img)

def partition_main_sides(images):
    side_partitions = []
    for img in images:
        sides = []
        sides.append(img.crop((105, 60, 361, 316)))
        sides.append(img.crop((384, 62, 640, 318)))
        sides.append(img.crop((658, 62, 914, 318)))
        sides.append(img.crop((86, 344, 342, 600)))
        sides.append(img.crop((373, 344, 629, 600)))
        sides.append(img.crop((648, 344, 904, 600)))
        side_partitions.extend(sides)
    return side_partitions

def partition_short_sides(images):
    side_partitions = []
    for img in images:
        sides = []
        sides.append(img.crop((30, 168, 202, 410)))
        sides.append(img.crop((238, 165, 400, 415)))
        sides.append(img.crop((30, 450, 200, 712)))
        sides.append(img.crop((238, 450, 400, 712)))
        side_partitions.extend(sides)
    return side_partitions

def partition_long_sides(images):
    side_partitions = []
    # Left side.
    side_partitions.append(images[0].crop((98, 144, 242, 356)))
    side_partitions.append(images[0].crop((282, 144, 425, 354)))
    side_partitions.append(images[0].crop((90, 388, 240, 714)))
    side_partitions.append(images[0].crop((282, 388, 430, 714)))
    side_partitions.append(images[0].crop((90, 748, 240, 956)))
    side_partitions.append(images[0].crop((282, 748, 430, 956)))
    # Right side.
    side_partitions.append(images[1].crop((100, 136, 240, 300)))
    side_partitions.append(images[1].crop((270, 134, 420, 300)))
    side_partitions.append(images[1].crop((90, 344, 240, 650)))
    side_partitions.append(images[1].crop((276, 344, 434, 650)))
    side_partitions.append(images[1].crop((80, 694, 240, 926)))
    side_partitions.append(images[1].crop((274, 690, 440, 926)))
    return side_partitions

def partition_sides(images):
    main_sides = partition_main_sides(images[0:2])
    short_sides = partition_short_sides(images[2:4])
    long_sides = partition_long_sides(images[4:6])
    return (main_sides, short_sides, long_sides)

def identify_side_features(sides, model):
    features = [0] * config.OUTPUT_DIM
    predictions = [0] * config.OUTPUT_DIM
    i = 0
    for side in sides:
        for img in side:
            reshaped = dataset.resize_img(dataset.pad_image(array(img)))
            pred = classifier.predict(model, reshaped)
            predict_label = classifier.get_best_prediction(pred)[0]
            predictions[i] = predict_label
            features[predict_label] += 1
            i += 1
    return (features, predictions)

def print_features(features):
    for feature, amount in enumerate(features):
        print(f"{config.LABELS[feature]} - {amount}")

if __name__ == "__main__":
    config.MAX_GPU_FRACTION = 0.2
    log("Loading classifier model...")
    MODEL = classifier.load_from_file("../resources/trained_models/model")

    log("Waiting for level selection...")
    log("Press S when a level has been selected.")
    sleep_until_start()

    start_level()

    log("Waiting for level to start...")
    wait_for_light()

    log("Inspecting bomb...")
    IMAGES = inspect_bomb()
    SIDE_PARTITIONS = partition_sides(IMAGES)
    FEATURES, PREDICTIONS = identify_side_features(SIDE_PARTITIONS, MODEL)

    cv2.namedWindow("Predictions")

    label = 0
    for side in SIDE_PARTITIONS:
        for img in side:
            pred_label = PREDICTIONS[label]
            print(f"Predicted: {pred_label} ({config.LABELS[pred_label]})")
            img = cv2.cvtColor(array(img, dtype="uint8"), cv2.COLOR_RGB2BGR)
            cv2.imshow("Predictions", img)
            label += 1
            key = cv2.waitKey(0)
            if key == ord('q'):
                break

    print_features(FEATURES)
