import jieba
import joblib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from app.models import POI

DATABASE_URL = "postgresql://poi:poipass@db:5432/poiplatform"

def tokenize(text: str) -> str:
    return " ".join(jieba.cut(text))

def load_data():
    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        pois = session.query(POI).filter(POI.category != "其他").all()

    texts, labels = [], []
    for poi in pois:
        text = poi.name
        if poi.description:
            text += " " + poi.description
        texts.append(tokenize(text))
        labels.append(poi.category)

    extra = [
        ("协和医院", "医疗"), ("人民医院", "医疗"), ("中医院", "医疗"),
        ("儿童医院", "医疗"), ("口腔医院", "医疗"), ("妇产医院", "医疗"),
        ("肿瘤医院", "医疗"), ("眼科医院", "医疗"), ("骨科医院", "医疗"),
        ("社区卫生服务中心", "医疗"), ("卫生院", "医疗"), ("药店", "医疗"),
        ("诊所", "医疗"), ("门诊", "医疗"), ("医务室", "医疗"),
        ("康复中心", "医疗"), ("体检中心", "医疗"), ("妇幼保健院", "医疗"),
        ("北京协和医院", "医疗"), ("北京儿童医院", "医疗"), ("北京口腔医院", "医疗"),
        ("海淀医院", "医疗"), ("朝阳医院", "医疗"), ("同仁医院", "医疗"),
        ("小学", "教育"), ("中学", "教育"), ("大学", "教育"),
        ("学院", "教育"), ("幼儿园", "教育"), ("培训班", "教育"),
        ("图书馆", "教育"), ("少年宫", "教育"), ("科技馆", "教育"),
        ("清华大学", "教育"), ("北京大学", "教育"), ("北师大", "教育"),
        ("清华大学附属小学", "教育"), ("人大附中", "教育"), ("北京四中", "教育"),
        ("新东方培训", "教育"), ("学而思", "教育"), ("教育培训", "教育"),
        ("地铁站", "交通"), ("公交站", "交通"), ("停车场", "交通"),
        ("高铁站", "交通"), ("火车站", "交通"), ("机场", "交通"),
        ("北京地铁", "交通"), ("北京西站", "交通"), ("首都机场", "交通"),
        ("餐厅", "餐饮"), ("饭店", "餐饮"), ("咖啡馆", "餐饮"),
        ("火锅店", "餐饮"), ("烤肉店", "餐饮"), ("快餐", "餐饮"),
        ("星巴克", "餐饮"), ("麦当劳", "餐饮"), ("肯德基", "餐饮"),
    ]
    for text, label in extra:
        texts.append(tokenize(text))
        labels.append(label)

    return texts, labels

def train():
    print("加载数据...")
    texts, labels = load_data()
    print(f"共 {len(texts)} 条有效样本，分类：{set(labels)}")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000, C=5.0))
    ])

    print("训练中...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    print("\n分类报告：")
    print(classification_report(y_test, y_pred))

    joblib.dump(pipeline, "/app/models/poi_classifier.pkl")
    print("模型已保存到 /app/models/poi_classifier.pkl")
if __name__ == "__main__":
    train()