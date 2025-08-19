from faker import Faker
import random

fake = Faker("pt_BR")


def fake_plate():
    return "".join(fake.random_letters(3)).upper() + str(random.randint(0,9)) + "".join(fake.random_letters(1)).upper() + str(random.randint(0,9)) + str(random.randint(0,9))
                                                          

def fake_entrys(count=1000):
    data = {}
    for i in range(count):
        data[fake_plate()] = [fake.name(),random.choice(["autorizado","não autorizado"])]

    return data

if __name__ == "__main__":

    file = open("fake_data.csv","w")
    entrys = fake_entrys(1000)
    for placa in entrys.keys():
        file.write(f"{placa};{entrys[placa][0]};{entrys[placa][1]}\n")
    file.close()