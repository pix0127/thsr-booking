# -*- coding: utf-8 -*-
import cv2
import numpy as np


def blur(img, size=3):
    return cv2.medianBlur(img, size)


def find_start_end(img):
    start_y = np.where(np.average(img[:, :3], axis=2) < 100)[0][-1]
    end_y = np.where(np.average(img[:, -3:], axis=2) < 100)[0][-1]
    return start_y, end_y


def linear_func(sy, ey, length=122):
    delta = (ey - sy) / length
    return [int(np.round(delta * i + sy)) for i in range(length)]


def _find_bound(img, sy, ey, up_b):
    y = linear_func(sy, ey, img.shape[1])
    low_b = -2
    impt = 0.9
    for i in range(1, img.shape[1]):
        y_center = int(np.round(impt * y[i - 1] + (1 - impt) * y[i]))
        rr = range(y_center + low_b, y_center + up_b)
        chunk = np.average(img[rr, i], axis=1)
        diff = np.abs(np.diff(chunk))
        max_idx = np.argmax(diff) if diff.max() > 50 else -low_b
        y[i] = min(y[i], max_idx + rr[0])
    return y


def find_bound(img, sy, ey):
    result = [_find_bound(img, sy, ey, up_b) for up_b in range(1, 4)]
    end_ys = [abs(y[-1] - ey) for y in result]
    return result[np.argmin(end_ys) - 1]


def adjust_line(img, y):
    yy = y.copy()
    th = 150
    for i in range(len(y)):
        for ii in range(1, 3):
            if abs(np.average(img[yy[i] + ii, i]) - np.average(img[yy[i], i])) > th:
                yy[i] = yy[i] + ii
                break
    return yy


def find_line(img, y):
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 2)
    poly = np.poly1d(coeffs)
    yy = np.round(poly(x)).astype(int)
    return adjust_line(img, yy)


def eliminate_line(image):
    dst = cv2.fastNlMeansDenoisingColored(image, None, 30, 30, 7, 21)
    sy, ey = find_start_end(dst)
    fdst = np.where(dst < 150, 0, dst)
    y = find_bound(fdst, sy, ey)
    dy = find_line(fdst, y)
    img = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY)
    yy = adjust_line(img, np.array(dy) - 4)
    for i in range(len(dy)):
        img[yy[i]:dy[i], i] = 255 - img[yy[i]:dy[i], i]
    return img


def clean_img(img):
    img = eliminate_line(img.copy())
    dst = cv2.fastNlMeansDenoising(img, None, 30, 7, 21)
    blur_img = blur(dst, 3)
    _, thresh = cv2.threshold(blur_img, 127, 255, 0)
    is_success, buffer = cv2.imencode(".jpg", thresh)
    return buffer


def extract(img):
    clean = clean_img(img)
    contours, _ = cv2.findContours(clean.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < 10 or h < 10:
            continue
        if x == 0 and y == 0:
            contour = np.delete(contour, np.where(contour[:, 0, 0] == 0)[0], axis=0)
            contour = np.delete(contour, np.where(contour[:, 0, 0] == clean.shape[1] - 1)[0], axis=0)
            x, y, w, h = cv2.boundingRect(contour)
        regions.append((x, y, w, h))

    regions = sorted(regions, key=lambda r: r[2] * r[3], reverse=True)[:4]
    letters = [clean[y:y + h, x:x + w] for x, y, w, h in regions]
    return regions, letters