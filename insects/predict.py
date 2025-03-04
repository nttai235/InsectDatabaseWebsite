import numpy as np
import os
import cv2
from ultralytics import YOLO
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
from django.conf import settings

class_names = [
    'Adristyrannus', 'Aleurocanthus spiniferus', 'Ampelophaga', 'Aphis citricola Vander Goot',
    'Apolygus lucorum', 'Bactrocera tsuneonis', 'Beet spot flies', 'Brevipoalpus lewisi McGregor',
    'Ceroplastes rubens', 'Chlumetia transversa', 'Chrysomphalus aonidum', 'Cicadella viridis',
    'Cicadellidae', 'Colomerus vitis', 'Dacus dorsalis(Hendel)', 'Dasineura sp',
    'Deporaus marginatus Pascoe', 'Erythroneura apicalis', 'Icerya purchasi Maskell',
    'Lawana imitata Melichar', 'Limacodidae', 'Locustoidea', 'Lycorma delicatula',
    'Mango flat beak leafhopper', 'Miridae', 'Nipaecoccus vastalor', 'Panonchus citri McGregor',
    'Papilio xuthus', 'Parlatoria zizyphus Lucus', 'Phyllocnistis citrella Stainton',
    'Phyllocoptes oleiverus ashmead', 'Pieris canidia', 'Polyphagotars onemus latus',
    'Potosiabre vitarsis', 'Prodenia litura', 'Pseudococcus comstocki Kuwana',
    'Rhytidodera bowrinii white', 'Rice Stemfly', 'Salurnis marginella Guerr',
    'Scirtothrips dorsalis Hood', 'Sternochetus frigidus', 'Tetradacus c Bactrocera minax',
    'Thrips', 'Toxoptera aurantii', 'Toxoptera citricidus', 'Trialeurodes vaporariorum',
    'Unaspis yanonensis', 'Viteus vitifoliae', 'Xylotrechus', 'alfalfa plant bug',
    'alfalfa seed chalcid', 'alfalfa weevil', 'aphids', 'army worm', 'asiatic rice borer',
    'beet army worm', 'beet fly', 'beet weevil', 'bird cherry-oataphid', 'black cutworm',
    'blister beetle', 'brown plant hopper', 'cabbage army worm', 'cerodonta denticornis',
    'corn borer', 'english grain aphid', 'flax budworm', 'flea beetle', 'grain spreader thrips',
    'green bug', 'grub', 'large cutworm', 'legume blister beetle', 'longlegged spider mite',
    'lytta polita', 'meadow moth', 'mole cricket', 'odontothrips loti', 'oides decempunctata',
    'paddy stem maggot', 'parathrene regalis', 'peach borer', 'penthaleus major', 'red spider',
    'rice gall midge', 'rice leaf caterpillar', 'rice leaf roller', 'rice leafhopper',
    'rice shell pest', 'rice water weevil', 'sericaorient alismots chulsky', 'small brown plant hopper',
    'tarnished plant bug', 'therioaphis maculata Buckton', 'wheat blossom midge',
    'wheat phloeothrips', 'wheat sawfly', 'white backed plant hopper', 'white margined moth',
    'wireworm', 'yellow cutworm', 'yellow rice borer'
]

# class_names = [
#     'acalymma', 'alticini', 'Squash_Bug', 'asparagus',
#     'aulacophora', 'dermaptera', 'leptinotarsa', 'mantodea',
#     'Achatina_fulica', 'Cerotoma_trifurcata'
# ]

# def load_and_preprocess_image(img_path):
#     img = image.load_img(img_path, target_size=(224, 224))
#     img_array = image.img_to_array(img)
#     img_array_expanded = np.expand_dims(img_array, axis=0)
#     return preprocess_input(img_array_expanded)
#
#
# def predict_image(img_path):
#     # Make sure the model path is correctly set
#     model_path = os.path.join(settings.MEDIA_ROOT, 'resnet50_model.h5')
#     model = load_model(model_path)
#     img_preprocessed = load_and_preprocess_image(img_path)
#     print('load_and_preprocess_image',img_preprocessed)
#     predictions = model.predict(img_preprocessed)
#     predicted_class_index = np.argmax(predictions[0])
#     print('predicted_class_index',predicted_class_index)
#     return class_names[predicted_class_index]

def predict_image(img_path):
    model_path = os.path.join(settings.MEDIA_ROOT, 'best_yolo11n_ip103.pt')
    model = YOLO(model_path)
    results = model.predict(source=img_path)
    img = cv2.imread(img_path)
    if len(results) > 0 and len(results[0].boxes) > 0:  # Đảm bảo có đối tượng được phát hiện
        boxes = results[0].boxes.xyxy  # Toạ độ (x1, y1, x2, y2)
        confidences = results[0].boxes.conf  # Độ tin cậy
        classes = results[0].boxes.cls  # Chỉ số lớp
        for i in range(len(boxes)):
            # Lấy toạ độ bounding box
            x1, y1, x2, y2 = map(int, boxes[i])  # Chuyển về kiểu int
            # Lấy độ tin cậy và nhãn lớp
            confidence = confidences[i].item()
            class_index = int(classes[i].item())
            label = f"{class_names[class_index]}: {confidence:.2f}"
            # Vẽ khung chữ nhật cho bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Màu xanh đỏ
            cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        # Lưu ảnh đã vẽ bounding box vào thư mục kết quả
        output_path = os.path.join(settings.MEDIA_ROOT, 'output_image.jpg')
        cv2.imwrite(output_path, img)
        print("Saved image with bounding boxes at:", output_path)
        # Trả về tên lớp dự đoán của đối tượng có độ tin cậy cao nhất
        best_index = confidences.argmax().item()
        predicted_class_index = int(classes[best_index])
        predicted_class_name = class_names[predicted_class_index]
        return output_path, predicted_class_name
    else:
        return "Không phát hiện đối tượng"