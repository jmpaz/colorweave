from collections import namedtuple
from math import sqrt
import random
from PIL import Image

Point = namedtuple("Point", ("coords", "n", "ct"))
Cluster = namedtuple("Cluster", ("points", "center", "n"))


# YUV implementation of `colorz` from https://charlesleifer.com/blog/using-python-and-k-means-to-find-the-dominant-colors-in-images/
def infer_palette(image_path, n=4):
    img = Image.open(image_path)
    img.thumbnail((200, 200))

    points = get_points(img)
    clusters = kmeans(points, n, 1)
    yuvs = [c.center.coords for c in clusters]
    return [yuv_to_hex(yuv) for yuv in yuvs]


# Conversion from RGB to YUV (BT.601)
def rgb_to_yuv(rgb):
    r, g, b = rgb
    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = -0.14713 * r - 0.28886 * g + 0.436 * b
    v = 0.615 * r - 0.51499 * g - 0.10001 * b
    return (y, u, v)


# Convert a YUV color back to hex representation
def yuv_to_hex(yuv):
    y, u, v = yuv
    r = y + 1.13983 * v
    g = y - 0.39465 * u - 0.58060 * v
    b = y + 2.03211 * u
    return "#%02x%02x%02x" % (int(r), int(g), int(b))


def get_points(img):
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        yuv = rgb_to_yuv(color[:3])
        points.append(Point(yuv, 3, count))
    return points


def euclidean(p1, p2):
    return sqrt(sum([(p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)]))


def calculate_center(points, n):
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += p.coords[i] * p.ct
    return Point([(v / plen) for v in vals], n, 1)


def kmeans(points, k, min_diff):
    clusters = [Cluster([p], p, p.n) for p in random.sample(points, k)]

    while True:
        plists = [[] for i in range(k)]

        for p in points:
            smallest_distance = float("Inf")
            for i in range(k):
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            break

    return clusters
