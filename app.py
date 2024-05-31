import csv
import io
import random
import string
from flask import Flask, Response, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo.mongo_client import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'ttsalfamart'

# Menghubungkan ke MongoDB
client = MongoClient("mongodbatlaslink")

# Cluster
db = client['tts_kapita'] 
# Collection
users_collection = db['users'] 
inventory_collection = db['inventory']
inventory_chart_data = db['inventory']
supplier_list = db['supplier']
shoplist = db['toko']
shipment_collection = db['shipment']

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return render_template('base.html')
        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/home')
def homedashboard():
    if 'username' in session:
        # Ambil ringkasan tabel dari setiap koleksi
        inventory_summary = inventory_collection.find()
        supplier_summary = supplier_list.find().limit(5)
        shoplist_summary = shoplist.find().limit(5)
        inventory_chart = inventory_chart_data.find()

        # Render template dengan data yang diambil
        return render_template('home.html', 
                                username=session['username'],
                                inventory_summary=inventory_summary, 
                                supplier_summary=supplier_summary, 
                                shoplist_summary=shoplist_summary,
                                inventory_chart=inventory_chart)
        
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'username' in session:
        if request.method == 'POST':
            kode_barang = request.form['new_kode_barang']
            nama_barang = request.form['new_nama_barang']
            stok_barang = int(request.form['new_stok_barang'])
            harga_barang = float(request.form['new_harga_barang'])
            # Mengecek apakah kode barang sudah ada dalam database
            if inventory_collection.find_one({'kode_barang': kode_barang}):
                # Jika sudah ada, set session untuk menampilkan alert
                flash('Kode barang sudah ada dalam database', 'danger')
                return redirect(url_for('inventory'))

            # Jika belum, maka tambahkan barang ke database
            inventory_collection.insert_one({
                'kode_barang': kode_barang,
                'nama_barang': nama_barang,
                'stok_barang': stok_barang,
                'harga_barang': harga_barang
            })
            flash('Barang berhasil ditambahkan', 'success')

        # Mendapatkan semua barang dari database
        barang = inventory_collection.find()
        return render_template('inventory.html', barang=barang)
    return render_template('login.html')    

    

@app.route('/update_barang/<string:item_id>', methods=['GET', 'POST'])
def update_barang(item_id):
    if 'username' in session:
        if request.method == 'POST':
            kode_barang = request.form['new_kode_barang']
            nama_barang = request.form['new_nama_barang']
            harga_barang = float(request.form['new_harga_barang'])

            # Lakukan update pada item dengan ID tertentu
            inventory_collection.update_one(
                {'_id': ObjectId(item_id)},
                {'$set': {'kode_barang': kode_barang, 'nama_barang': nama_barang, 'harga_barang': harga_barang}}
            )

            return redirect(url_for('inventory'))

        # Dapatkan detail barang berdasarkan ID
        barang = inventory_collection.find_one({'_id': ObjectId(item_id)})
        return render_template('inventory.html', barang=barang)
    return render_template('login.html')

@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' in session :
        if request.method == 'POST':
            kode_barang = request.form['kode_barang']
            supplier = request.form['supplier']
            jumlah_barang = int(request.form['jumlah_barang'])
            nomor_pesanan = 'P' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Generate random nomor pesanan

            # Cek apakah barang tersedia di inventaris
            barang = inventory_collection.find_one({'kode_barang': kode_barang})
            if barang:
                # Cek apakah supplier tersedia di database
                supplier_data = supplier_list.find_one({'nama_supplier': supplier})
                if supplier_data:
                    # Lakukan proses order barang jika jumlah tersedia di inventaris
                    # Tambahkan stok barang di inventaris
                    inventory_collection.update_one({'_id': barang['_id']}, {'$inc': {'stok_barang': jumlah_barang}})
                    # Simpan informasi pemesanan ke database
                    order_data = {
                        'kode_barang': kode_barang,
                        'supplier': supplier,
                        'jumlah_barang': jumlah_barang,
                        'nomor_pesanan': nomor_pesanan
                    }
                    db['orders'].insert_one(order_data)
                    flash('Barang berhasil diorder', 'success')
                else:
                    flash('Supplier tidak ditemukan', 'danger')
            else:
                flash('Barang tidak ditemukan', 'danger')
            return redirect(url_for('order'))

        # Dapatkan daftar barang dan supplier untuk ditampilkan di form order
        daftar_barang = inventory_collection.find({}, {'kode_barang': 1, '_id': 0})  # Dapatkan daftar kode barang saja dari database
        daftar_kode_barang = [barang['kode_barang'] for barang in daftar_barang]  # Buat list kode barang
        daftar_suppliers = supplier_list.find({}, {'nama_supplier': 1, '_id': 0})  # Dapatkan daftar supplier saja dari database
        daftar_nama_supplier = [supplier['nama_supplier'] for supplier in daftar_suppliers]  # Buat list nama supplier
        return render_template('order.html', daftar_kode_barang=daftar_kode_barang, daftar_nama_supplier=daftar_nama_supplier)
    return render_template('login.html')

@app.route('/report')
def report():
    if 'username' in session:
        # Mengambil data dari MongoDB
        daftar_inventory = inventory_collection.find()
        daftar_order = db['orders'].find()
        daftar_shipment = shipment_collection.find()

        # Kirim data ke template HTML
        return render_template('report.html', 
                               daftar_inventory=daftar_inventory, 
                               order_data=daftar_order, 
                               shipment_data=daftar_shipment)
    return render_template('login.html')

@app.route('/export_all_csv')
def export_all_csv():
    if 'username' in session:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write Inventory Report to CSV
        writer.writerow(['Inventory Report'])
        writer.writerow(['Kode Barang', 'Nama Barang', 'Stok Barang', 'Harga Barang'])
        for item in inventory_collection.find():
            writer.writerow([item['kode_barang'], item['nama_barang'], item['stok_barang'], item['harga_barang']])
        writer.writerow([])

        # Write Order Report to CSV
        writer.writerow(['Order Report'])
        writer.writerow(['Kode Barang', 'Supplier', 'Jumlah Barang', 'Nomor Pesanan'])
        for order in db['orders'].find():
            writer.writerow([order['kode_barang'], order['supplier'], order['jumlah_barang'], order['nomor_pesanan']])
        writer.writerow([])

        # Write Shipment Report to CSV
        writer.writerow(['Shipment Report'])
        writer.writerow(['Kode Barang', 'Nama Toko', 'Jumlah Barang', 'Kode Pengiriman'])
        for shipment in shipment_collection.find():
            writer.writerow([shipment['kode_barang'], shipment['nama_toko'], shipment['jumlah_barang'], shipment['nomor_pengiriman']])

        output.seek(0)
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=all_report.csv"})
    
    return render_template('login.html')


@app.route('/supplier', methods=['GET', 'POST'])
def supplier():
    if 'username' in session:
        if request.method == 'POST':
            nama_supplier = request.form['nama_supplier']
            alamat_supplier = request.form['alamat_supplier']
            telepon_supplier = request.form['telepon_supplier']

            supplier_list.insert_one({
                'nama_supplier': nama_supplier,
                'alamat': alamat_supplier,
                'telepon': telepon_supplier
            })
            flash('Supplier berhasil ditambahkan', 'success')
            return redirect(url_for('supplier'))

        suppliers = supplier_list.find()
        return render_template('supplier.html', suppliers=suppliers)
    return render_template('login.html')

@app.route('/update_supplier/<string:supplier_id>', methods=['POST'])
def update_supplier(supplier_id):
    if 'username' in session:
        nama_supplier = request.form['nama_supplier']
        alamat_supplier = request.form['alamat_supplier']
        telepon_supplier = int(request.form['telepon_supplier'])

        supplier_list.update_one(
            {'_id': ObjectId(supplier_id)},
            {'$set': {'nama_supplier': nama_supplier, 'alamat': alamat_supplier, 'telepon': telepon_supplier}}
        )
        flash('Supplier berhasil diupdate', 'success')
        return redirect(url_for('supplier'))
    return render_template('login.html')

@app.route('/hapus_supplier/<string:supplier_id>', methods=['POST'])
def hapus_supplier(supplier_id):
    if 'username' in session:
        supplier_list.delete_one({'_id': ObjectId(supplier_id)})
        flash('Supplier berhasil dihapus', 'success')
        return redirect(url_for('supplier'))
    return render_template('login.html')

@app.route('/toko', methods=['GET', 'POST'])
def toko():
    if 'username' in session:
        if request.method == 'POST':
            nama_toko = request.form['nama_toko']
            alamat_toko = request.form['alamat_toko']
            kontak_toko = request.form['kontak_toko']

            shoplist.insert_one({
                'nama_toko': nama_toko,
                'alamat_toko': alamat_toko,
                'kontak_toko': kontak_toko
            })
            flash('Toko berhasil ditambahkan', 'success')
            return redirect(url_for('toko'))

        tokos = shoplist.find()
        return render_template('toko.html', tokos=tokos)
    return render_template('login.html')

@app.route('/update_toko/<string:toko_id>', methods=['POST'])
def update_toko(toko_id):
    if 'username' in session:
        nama_toko = request.form['nama_toko']
        alamat_toko = request.form['alamat_toko']
        kontak_toko = request.form['kontak_toko']

        shoplist.update_one(
            {'_id': ObjectId(toko_id)},
            {'$set': {'nama_toko': nama_toko, 'alamat_toko': alamat_toko, 'kontak_toko': kontak_toko}}
        )
        flash('Toko berhasil diupdate', 'success')
        return redirect(url_for('toko'))
    return render_template('login.html')

@app.route('/hapus_toko/<string:toko_id>', methods=['POST'])
def hapus_toko(toko_id):
    if 'username' in session:
        shoplist.delete_one({'_id': ObjectId(toko_id)})
        flash('Toko berhasil dihapus', 'success')
        return redirect(url_for('toko'))
    return render_template('login.html')

@app.route('/shipment', methods=['GET','POST'])
def shipment():
    if 'username' in session:
        if request.method == 'POST':
            kode_barang = request.form['kode_barang']
            nama_toko = request.form['toko_id']
            jumlah_barang = int(request.form['jumlah_barang'])
            nomor_pengiriman = 'K' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            barang = inventory_collection.find_one({'kode_barang': kode_barang})
            if barang:
                if barang['stok_barang'] >= jumlah_barang:
                    inventory_collection.update_one(
                        {'_id': barang['_id']},
                        {'$inc': {'stok_barang': -jumlah_barang}}
                    )
                    shipment_data = {
                        'kode_barang': kode_barang,
                        'nama_toko' : nama_toko,
                        'jumlah_barang': jumlah_barang,
                        'nomor_pengiriman' : nomor_pengiriman
                    }
                    shipment_collection.insert_one(shipment_data)
                    flash('Barang berhasil dikirim', 'success')
                else:
                    flash('Stok barang tidak mencukupi', 'danger')
            else:
                flash('Barang tidak ditemukan', 'danger')
            return redirect(url_for('shipment'))

        daftar_barang = inventory_collection.find({}, {'kode_barang': 1, '_id': 0})
        daftar_kode_barang = [barang['kode_barang'] for barang in daftar_barang]
        daftar_toko = shoplist.find({}, {'nama_toko': 1, '_id': 1})
        return render_template('shipment.html', daftar_kode_barang=daftar_kode_barang, daftar_toko=daftar_toko)
    return render_template('login.html')

@app.route('/hapus_barang/<string:item_id>', methods=['POST'])
def hapus_barang(item_id):
    if 'username' in session:
        inventory_collection.delete_one({'_id': ObjectId(item_id)})
        flash('Barang berhasil dihapus')
        return redirect(url_for('inventory'))
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
